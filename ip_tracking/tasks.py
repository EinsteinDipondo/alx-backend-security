from celery import shared_task
from django.utils import timezone
from django.db.models import Count, Q, F
from django.db import transaction
from datetime import timedelta
import logging
from .models import (
    RequestLog, 
    SuspiciousIP, 
    BlockedIP,
    AnomalyDetectionConfig
)
from django.conf import settings
from django.core.mail import send_mail
import json
from collections import defaultdict

logger = logging.getLogger(__name__)

@shared_task
def detect_anomalies():
    """
    Hourly task to detect suspicious IP activity.
    Flags IPs exceeding 100 requests/hour or accessing sensitive paths.
    """
    try:
        logger.info("Starting anomaly detection task...")
        
        # Get active configuration
        config = AnomalyDetectionConfig.objects.filter(enabled=True).first()
        if not config:
            # Create default configuration if none exists
            config = AnomalyDetectionConfig.objects.create(
                name="Default Anomaly Detection",
                description="Default configuration for detecting suspicious activity",
                threshold=100,
                time_window_hours=1,
                sensitive_paths="/admin,/login,/wp-login.php,/phpmyadmin,/config,.env",
                severity_level='medium'
            )
        
        # Get time threshold (last hour by default)
        time_threshold = timezone.now() - timedelta(hours=config.time_window_hours)
        
        # Detect high frequency requests
        if config.check_frequency:
            detect_high_frequency_ips(time_threshold, config)
        
        # Detect sensitive path access
        if config.check_sensitive_paths:
            detect_sensitive_path_access(time_threshold, config)
        
        # Detect error patterns
        if config.check_error_rate:
            detect_error_patterns(time_threshold, config)
        
        logger.info("Anomaly detection task completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Anomaly detection task failed: {e}")
        send_alert_email("Anomaly Detection Task Failed", str(e))
        return False


def detect_high_frequency_ips(time_threshold, config):
    """
    Detect IPs with high request frequency.
    """
    logger.info(f"Detecting high frequency IPs (> {config.threshold} reqs/hour)...")
    
    # Group logs by IP in the time window
    ip_counts = RequestLog.objects.filter(
        timestamp__gte=time_threshold
    ).values('ip_address').annotate(
        request_count=Count('id'),
        paths=Count('path', distinct=True),
        last_request=models.Max('timestamp')
    ).filter(
        request_count__gt=config.threshold
    ).order_by('-request_count')
    
    suspicious_count = 0
    
    for ip_data in ip_counts:
        ip_address = ip_data['ip_address']
        request_count = ip_data['request_count']
        
        # Check if already blocked
        if BlockedIP.objects.filter(ip_address=ip_address).exists():
            continue
        
        # Create or update suspicious IP record
        suspicious_ip, created = SuspiciousIP.objects.update_or_create(
            ip_address=ip_address,
            reason='high_frequency',
            defaults={
                'severity': config.severity_level,
                'request_count': request_count,
                'details': {
                    'request_count': request_count,
                    'unique_paths': ip_data['paths'],
                    'last_request': ip_data['last_request'].isoformat() if ip_data['last_request'] else None,
                    'threshold': config.threshold,
                    'time_window': f"{config.time_window_hours} hour(s)",
                },
                'is_active': True,
            }
        )
        
        # Mark related logs as suspicious
        RequestLog.objects.filter(
            ip_address=ip_address,
            timestamp__gte=time_threshold
        ).update(
            is_suspicious=True,
            anomaly_reason=f"High frequency: {request_count} requests in {config.time_window_hours} hour(s)"
        )
        
        # Auto-block if configured
        if config.auto_block and request_count > config.threshold * 2:
            auto_block_ip(ip_address, 'high_frequency', suspicious_ip)
            suspicious_ip.auto_blocked = True
            suspicious_ip.save()
        
        suspicious_count += 1
        
        # Send alert for critical cases
        if request_count > config.threshold * 5:
            send_alert_email(
                f"Critical: High Frequency IP Detected - {ip_address}",
                f"IP {ip_address} made {request_count} requests in the last hour "
                f"(threshold: {config.threshold})."
            )
    
    logger.info(f"Found {suspicious_count} IPs with high frequency")


def detect_sensitive_path_access(time_threshold, config):
    """
    Detect IPs accessing sensitive paths.
    """
    logger.info("Detecting sensitive path access...")
    
    sensitive_paths = config.get_sensitive_paths_list()
    if not sensitive_paths:
        logger.info("No sensitive paths configured")
        return
    
    # Build query for sensitive paths
    sensitive_path_q = Q()
    for path in sensitive_paths:
        if path.startswith('/'):
            sensitive_path_q |= Q(path__startswith=path)
        else:
            sensitive_path_q |= Q(path__contains=path)
    
    # Find IPs accessing sensitive paths
    sensitive_access = RequestLog.objects.filter(
        timestamp__gte=time_threshold,
        sensitive_path_q
    ).values('ip_address').annotate(
        access_count=Count('id'),
        paths=Count('path', distinct=True),
        unique_paths_list=models.functions.GroupConcat('path', distinct=True)
    ).order_by('-access_count')
    
    suspicious_count = 0
    
    for ip_data in sensitive_access:
        ip_address = ip_data['ip_address']
        access_count = ip_data['access_count']
        
        # Check if already blocked
        if BlockedIP.objects.filter(ip_address=ip_address).exists():
            continue
        
        # Get the actual paths accessed
        paths = getattr(ip_data, 'unique_paths_list', '').split(',')[:5]
        
        # Create or update suspicious IP record
        suspicious_ip, created = SuspiciousIP.objects.update_or_create(
            ip_address=ip_address,
            reason='sensitive_paths',
            defaults={
                'severity': 'high' if access_count > 10 else config.severity_level,
                'request_count': access_count,
                'details': {
                    'access_count': access_count,
                    'sensitive_paths_accessed': paths,
                    'unique_path_count': ip_data['paths'],
                    'time_window': f"{config.time_window_hours} hour(s)",
                },
                'is_active': True,
            }
        )
        
        # Mark related sensitive path logs as suspicious
        RequestLog.objects.filter(
            ip_address=ip_address,
            timestamp__gte=time_threshold,
            sensitive_path_q
        ).update(
            is_suspicious=True,
            anomaly_reason=f"Sensitive path access: {access_count} attempts"
        )
        
        # Auto-block if configured and accessed multiple sensitive paths
        if config.auto_block and ip_data['paths'] > 2:
            auto_block_ip(ip_address, 'sensitive_paths', suspicious_ip)
            suspicious_ip.auto_blocked = True
            suspicious_ip.save()
        
        suspicious_count += 1
        
        # Send alert for multiple sensitive path access
        if ip_data['paths'] > 3:
            send_alert_email(
                f"Alert: Multiple Sensitive Path Access - {ip_address}",
                f"IP {ip_address} accessed {ip_data['paths']} different sensitive paths "
                f"({access_count} total attempts).\n\nPaths: {', '.join(paths)}"
            )
    
    logger.info(f"Found {suspicious_count} IPs accessing sensitive paths")


def detect_error_patterns(time_threshold, config):
    """
    Detect IPs with high error rates.
    """
    logger.info("Detecting error patterns...")
    
    # Find IPs with high error rates (4xx and 5xx responses)
    error_ips = RequestLog.objects.filter(
        timestamp__gte=time_threshold
    ).extra(
        select={'status_class': "SUBSTRING(CAST(status_code AS TEXT), 1, 1)"}
    ).filter(
        status_class__in=['4', '5']
    ).values('ip_address').annotate(
        total_requests=Count('id'),
        error_requests=Count('id', filter=Q(status_class__in=['4', '5'])),
        error_rate=Count('id', filter=Q(status_class__in=['4', '5'])) * 100.0 / Count('id')
    ).filter(
        error_rate__gt=50.0,  # More than 50% errors
        total_requests__gt=10  # At least 10 requests
    ).order_by('-error_rate')
    
    suspicious_count = 0
    
    for ip_data in error_ips:
        ip_address = ip_data['ip_address']
        error_rate = ip_data['error_rate']
        total_requests = ip_data['total_requests']
        error_requests = ip_data['error_requests']
        
        # Create or update suspicious IP record
        suspicious_ip, created = SuspiciousIP.objects.update_or_create(
            ip_address=ip_address,
            reason='multiple_errors',
            defaults={
                'severity': 'high' if error_rate > 80 else 'medium',
                'request_count': total_requests,
                'details': {
                    'total_requests': total_requests,
                    'error_requests': error_requests,
                    'error_rate': round(error_rate, 2),
                    'time_window': f"{config.time_window_hours} hour(s)",
                },
                'is_active': True,
            }
        )
        
        # Mark error logs as suspicious
        RequestLog.objects.filter(
            ip_address=ip_address,
            timestamp__gte=time_threshold,
            status_code__gte=400
        ).update(
            is_suspicious=True,
            anomaly_reason=f"High error rate: {round(error_rate, 1)}%"
        )
        
        suspicious_count += 1
        
        # Send alert for very high error rates
        if error_rate > 80:
            send_alert_email(
                f"Alert: High Error Rate - {ip_address}",
                f"IP {ip_address} has {error_rate:.1f}% error rate "
                f"({error_requests}/{total_requests} requests)."
            )
    
    logger.info(f"Found {suspicious_count} IPs with high error rates")


@shared_task
def auto_block_ip(ip_address, reason, suspicious_ip_id=None):
    """
    Automatically block an IP address.
    """
    try:
        # Check if already blocked
        if BlockedIP.objects.filter(ip_address=ip_address).exists():
            return False
        
        # Create block entry (24 hour temporary block)
        expires_at = timezone.now() + timedelta(hours=24)
        
        block = BlockedIP.objects.create(
            ip_address=ip_address,
            reason=f"Auto-blocked: {reason}",
            expires_at=expires_at
        )
        
        # Update suspicious IP record if provided
        if suspicious_ip_id:
            try:
                suspicious_ip = SuspiciousIP.objects.get(id=suspicious_ip_id)
                suspicious_ip.auto_blocked = True
                suspicious_ip.save()
            except SuspiciousIP.DoesNotExist:
                pass
        
        logger.info(f"Auto-blocked IP: {ip_address} - Reason: {reason}")
        
        # Send alert
        send_alert_email(
            f"IP Auto-blocked: {ip_address}",
            f"IP {ip_address} has been automatically blocked.\n"
            f"Reason: {reason}\n"
            f"Expires: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to auto-block IP {ip_address}: {e}")
        return False


@shared_task
def clear_old_suspicious_ips():
    """
    Clean up old suspicious IP records (older than 7 days).
    """
    try:
        time_threshold = timezone.now() - timedelta(days=7)
        
        # Mark old inactive records as resolved
        SuspiciousIP.objects.filter(
            last_detected__lt=time_threshold,
            is_active=False
        ).delete()
        
        # Mark very old active records as inactive
        SuspiciousIP.objects.filter(
            last_detected__lt=timezone.now() - timedelta(days=30),
            is_active=True
        ).update(is_active=False)
        
        logger.info("Cleared old suspicious IP records")
        return True
        
    except Exception as e:
        logger.error(f"Failed to clear old suspicious IPs: {e}")
        return False


@shared_task
def analyze_ip_behavior(ip_address, hours=24):
    """
    Analyze behavior of a specific IP address.
    """
    try:
        time_threshold = timezone.now() - timedelta(hours=hours)
        
        # Get all logs for this IP
        logs = RequestLog.objects.filter(
            ip_address=ip_address,
            timestamp__gte=time_threshold
        ).order_by('timestamp')
        
        if not logs:
            return {"error": "No logs found for this IP"}
        
        # Calculate statistics
        total_requests = logs.count()
        unique_paths = logs.values('path').distinct().count()
        
        # Calculate requests per hour
        if total_requests > 1:
            time_span = (logs.last().timestamp - logs.first().timestamp).total_seconds() / 3600
            requests_per_hour = total_requests / max(time_span, 1)
        else:
            requests_per_hour = total_requests
        
        # Calculate error rate
        error_logs = logs.filter(status_code__gte=400)
        error_rate = (error_logs.count() / total_requests * 100) if total_requests > 0 else 0
        
        # Check for sensitive path access
        config = AnomalyDetectionConfig.objects.filter(enabled=True).first()
        sensitive_paths = config.get_sensitive_paths_list() if config else []
        
        sensitive_access = logs.filter(
            Q(path__in=sensitive_paths) if sensitive_paths else Q()
        ).count()
        
        # Build analysis result
        analysis = {
            'ip_address': ip_address,
            'analysis_period_hours': hours,
            'total_requests': total_requests,
            'unique_paths': unique_paths,
            'requests_per_hour': round(requests_per_hour, 2),
            'error_rate': round(error_rate, 2),
            'sensitive_access_count': sensitive_access,
            'first_request': logs.first().timestamp.isoformat(),
            'last_request': logs.last().timestamp.isoformat(),
            'suspicious': False,
            'reasons': [],
        }
        
        # Check against thresholds
        if config:
            if requests_per_hour > config.threshold:
                analysis['suspicious'] = True
                analysis['reasons'].append(
                    f"High frequency: {round(requests_per_hour, 1)} requests/hour "
                    f"(threshold: {config.threshold})"
                )
            
            if sensitive_access > 0:
                analysis['suspicious'] = True
                analysis['reasons'].append(
                    f"Accessed {sensitive_access} sensitive paths"
                )
            
            if error_rate > 50:
                analysis['suspicious'] = True
                analysis['reasons'].append(
                    f"High error rate: {round(error_rate, 1)}%"
                )
        
        return analysis
        
    except Exception as e:
        logger.error(f"Failed to analyze IP {ip_address}: {e}")
        return {"error": str(e)}


def send_alert_email(subject, message):
    """
    Send alert email to administrators.
    """
    try:
        if not hasattr(settings, 'ADMIN_EMAILS'):
            logger.warning("ADMIN_EMAILS not configured, skipping email alert")
            return
        
        send_mail(
            subject=f"[IP Tracking Alert] {subject}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=settings.ADMIN_EMAILS,
            fail_silently=True,
        )
        
        logger.info(f"Alert email sent: {subject}")
        
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")


@shared_task
def generate_daily_report():
    """
    Generate daily anomaly detection report.
    """
    try:
        yesterday = timezone.now() - timedelta(days=1)
        
        # Get statistics
        total_suspicious = SuspiciousIP.objects.filter(
            first_detected__gte=yesterday
        ).count()
        
        new_blocks = BlockedIP.objects.filter(
            created_at__gte=yesterday
        ).count()
        
        auto_blocks = BlockedIP.objects.filter(
            created_at__gte=yesterday,
            reason__startswith="Auto-blocked"
        ).count()
        
        top_suspicious = SuspiciousIP.objects.filter(
            first_detected__gte=yesterday
        ).order_by('-request_count')[:10]
        
        # Generate report
        report_lines = [
            "=== Daily Anomaly Detection Report ===",
            f"Date: {timezone.now().strftime('%Y-%m-%d')}",
            f"Period: Last 24 hours",
            "",
            "Summary:",
            f"  - Suspicious IPs detected: {total_suspicious}",
            f"  - New blocks: {new_blocks}",
            f"  - Auto-blocks: {auto_blocks}",
            "",
            "Top Suspicious IPs:",
        ]
        
        for ip in top_suspicious:
            report_lines.append(
                f"  - {ip.ip_address}: {ip.reason} "
                f"({ip.request_count} requests, severity: {ip.severity})"
            )
        
        report = "\n".join(report_lines)
        
        # Send report
        send_alert_email("Daily Anomaly Detection Report", report)
        
        logger.info("Daily report generated and sent")
        return report
        
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        return None
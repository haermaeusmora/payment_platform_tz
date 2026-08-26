import hmac
import hashlib
import json
import urllib.request
import urllib.error
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from ..models import Notification, Invoice


class NotificationService:
    @classmethod
    def create_notification(cls, invoice):
        project = invoice.project
        
        if not project.notification_url:
            return None
        
        payload = cls._build_payload(invoice)
        signature = cls._generate_signature(payload, project.api_key)
        
        notification = Notification.objects.create(
            invoice=invoice,
            project=project,
            url=project.notification_url,
            payload=payload,
            signature=signature,
            status=Notification.Status.PENDING,
            next_retry_at=timezone.now()
        )
        
        return notification

    @classmethod
    def _build_payload(cls, invoice):
        total_paid = sum(p.credited_amount or p.amount for p in invoice.payments.all())
        
        return {
            'invoice_id': invoice.id,
            'external_id': invoice.external_id,
            'status': invoice.status,
            'amount': str(invoice.amount),
            'currency': invoice.currency,
            'total_paid': str(total_paid),
            'project_id': invoice.project.id,
            'merchant_id': invoice.project.merchant.id,
            'created_at': invoice.created_at.isoformat(),
            'updated_at': timezone.now().isoformat()
        }

    @classmethod
    def _generate_signature(cls, payload, api_key):
        message = json.dumps(payload, sort_keys=True)
        return hmac.new(
            api_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    @classmethod
    def process_pending_notifications(cls):
        notifications = Notification.objects.filter(
            status__in=[Notification.Status.PENDING, Notification.Status.RETRY],
            next_retry_at__lte=timezone.now()
        ).select_related('invoice', 'project')
        
        processed = 0
        for notification in notifications:
            if cls._send_notification(notification):
                processed += 1
        
        return processed

    @classmethod
    def _send_notification(cls, notification):
        notification.attempt_count += 1
        notification.last_attempt_at = timezone.now()
        
        try:
            data = json.dumps(notification.payload).encode('utf-8')
            req = urllib.request.Request(
                notification.url,
                data=data,
                headers={
                    'X-Signature': notification.signature,
                    'Content-Type': 'application/json'
                },
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                response_body = response.read().decode('utf-8')
                notification.response_status = response.status
                notification.response_body = response_body[:500]
                
                if 200 <= response.status < 300:
                    notification.status = Notification.Status.SENT
                    notification.save()
                    return True
                else:
                    return cls._handle_failed_notification(notification)
                
        except urllib.error.URLError as e:
            notification.error_message = str(e)[:500]
            return cls._handle_failed_notification(notification)
        except Exception as e:
            notification.error_message = str(e)[:500]
            return cls._handle_failed_notification(notification)

    @classmethod
    def _handle_failed_notification(cls, notification):
        if notification.attempt_count >= notification.max_attempts:
            notification.status = Notification.Status.EXPIRED
            notification.save()
            return False
        
        delay_minutes = 5 * (2 ** (notification.attempt_count - 1))
        notification.next_retry_at = timezone.now() + timezone.timedelta(minutes=delay_minutes)
        notification.status = Notification.Status.RETRY
        notification.save()
        return False
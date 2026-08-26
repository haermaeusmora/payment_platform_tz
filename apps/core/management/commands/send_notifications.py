from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from ...models import Notification
from ...services.notification_service import NotificationService


class Command(BaseCommand):
    help = 'Send pending notifications with retry logic'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of notifications to process in one batch'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        self.stdout.write(f'Starting to send notifications (batch size: {batch_size})...')
        
        processed = 0
        success = 0
        failed = 0
        
        while True:
            with transaction.atomic():
                notifications = Notification.objects.select_for_update().filter(
                    status__in=[Notification.Status.PENDING, Notification.Status.RETRY],
                    next_retry_at__lte=timezone.now()
                )[:batch_size]
                
                if not notifications:
                    break
                
                for notification in notifications:
                    self.stdout.write(f'Processing notification {notification.id}...', ending=' ')
                    
                    try:
                        sent = NotificationService._send_notification(notification)
                        if sent:
                            success += 1
                            self.stdout.write(self.style.SUCCESS('SENT'))
                        else:
                            failed += 1
                            self.stdout.write(self.style.WARNING('FAILED'))
                    except Exception as e:
                        failed += 1
                        notification.status = Notification.Status.FAILED
                        notification.error_message = str(e)[:500]
                        notification.save()
                        self.stdout.write(self.style.ERROR(f'ERROR: {str(e)[:50]}'))
                    
                    processed += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Processed: {processed}, Success: {success}, Failed: {failed}'
        ))
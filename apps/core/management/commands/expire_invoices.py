from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from ...models import Invoice
from ...services.notification_service import NotificationService


class Command(BaseCommand):
    help = 'Expire invoices that have passed their expiration date'

    def handle(self, *args, **options):
        self.stdout.write('Starting to expire invoices...')
        
        expired_count = 0
        batch_size = 1000

        while True:
            with transaction.atomic():
                invoices = Invoice.objects.filter(
                    status__in=[Invoice.Status.NEW, Invoice.Status.PENDING],
                    expires_at__lte=timezone.now()
                )[:batch_size]
                
                if not invoices:
                    break

                invoice_ids = []
                for invoice in invoices:
                    invoice.status = Invoice.Status.EXPIRED
                    invoice.save()
                    invoice_ids.append(invoice.id)
                    
                    # Создаем уведомление
                    NotificationService.create_notification(invoice)
                
                expired_count += len(invoice_ids)
                
                self.stdout.write(f'Expired {len(invoice_ids)} invoices...')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully expired {expired_count} invoices')
        )
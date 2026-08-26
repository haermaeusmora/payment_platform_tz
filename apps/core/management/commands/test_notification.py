from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from ...models import Merchant, Project, Invoice, ExchangeRate
from ...services import PaymentService


class Command(BaseCommand):
    help = 'Test notification system'

    def handle(self, *args, **options):
        self.stdout.write('Testing notification system...')
        
        merchant, _ = Merchant.objects.get_or_create(
            name="Test Merchant",
            defaults={"is_active": True}
        )
        self.stdout.write(f'Merchant: {merchant.id}')
        
        project, created = Project.objects.get_or_create(
            api_key="test-key-123",
            defaults={
                "merchant": merchant,
                "name": "Test Project",
                "notification_url": "https://webhook.site/b751b936-7efe-416f-be41-020d9d51debd",
                "is_active": True
            }
        )
        if created:
            self.stdout.write(f'Created project: {project.id}')
        else:
            self.stdout.write(f'Using existing project: {project.id}')

        ExchangeRate.objects.get_or_create(
            from_currency="USD",
            to_currency="USD",
            defaults={
                "rate": Decimal('1.000000'),
                "timestamp": timezone.now()
            }
        )
        self.stdout.write('Exchange rate ready')
        
        import uuid
        external_id = f"INV-TEST-{uuid.uuid4().hex[:8]}"
        
        invoice = Invoice.objects.create(
            project=project,
            amount=Decimal('100.00'),
            currency="USD",
            external_id=external_id,
            expires_at=timezone.now() + timezone.timedelta(days=7)
        )
        self.stdout.write(f'Created invoice: {invoice.id} ({external_id})')
        
        payment = PaymentService.process_payment(
            invoice_id=invoice.id,
            provider_transaction_id=f"txn-{uuid.uuid4().hex[:8]}",
            amount=Decimal('100.00'),
            currency="USD",
            received_at=timezone.now()
        )
        self.stdout.write(f'Processed payment: {payment.id}')
        
        from ...models import Notification
        notifications = Notification.objects.filter(invoice=invoice)
        
        self.stdout.write(f'Created {notifications.count()} notifications')
        
        for n in notifications:
            self.stdout.write(f'  Notification {n.id}: {n.status}')
            self.stdout.write(f'    URL: {n.url}')
            self.stdout.write(f'    Payload: {n.payload}')
            self.stdout.write(f'    Signature: {n.signature[:30]}...')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Done!'))
        self.stdout.write('\n📨 Run: python manage.py send_notifications')
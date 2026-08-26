from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from ..models import Merchant, Project, Invoice, ExchangeRate
from ..services.invoice_service import InvoiceService
from ..services.payment_service import PaymentService
from ..services.balance_service import BalanceService


class InvoiceServiceTest(TestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(name="Test Merchant")
        self.project = Project.objects.create(
            merchant=self.merchant,
            name="Test Project",
            api_key="test-key-123"
        )
    
    def test_create_invoice(self):
        invoice = InvoiceService.create_invoice(
            project=self.project,
            external_id="INV-001",
            amount=Decimal('100.00'),
            currency="USD",
            expires_at=timezone.now() + timezone.timedelta(days=7)
        )
        
        self.assertEqual(invoice.amount, Decimal('100.00'))
        self.assertEqual(invoice.status, Invoice.Status.NEW)


class BalanceServiceTest(TestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(name="Test Merchant")
        self.project = Project.objects.create(
            merchant=self.merchant,
            name="Test Project",
            api_key="test-key-123"
        )
        self.invoice = Invoice.objects.create(
            project=self.project,
            amount=Decimal('100.00'),
            currency="USD",
            external_id="INV-001",
            expires_at=timezone.now() + timezone.timedelta(days=7)
        )
        ExchangeRate.objects.create(
            from_currency="USD",
            to_currency="USD",
            rate=Decimal('1.0'),
            timestamp=timezone.now()
        )
    
    def test_balance_calculation(self):
        balances = BalanceService.get_balance(self.merchant.id)
        self.assertEqual(balances.get('USD', Decimal('0.00')), Decimal('0.00'))
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from ..models import Merchant, Project, Invoice, Payment, LedgerEntry


class MerchantModelTest(TestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(
            name="Test Merchant",
            is_active=True
        )
    
    def test_merchant_creation(self):
        self.assertEqual(self.merchant.name, "Test Merchant")
        self.assertTrue(self.merchant.is_active)
        self.assertIsNotNone(self.merchant.created_at)


class InvoiceModelTest(TestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(name="Test Merchant")
        self.project = Project.objects.create(
            merchant=self.merchant,
            name="Test Project",
            api_key="test-key-123",
            is_active=True
        )
        self.invoice = Invoice.objects.create(
            project=self.project,
            amount=Decimal('100.00'),
            currency="USD",
            external_id="INV-001",
            expires_at=timezone.now() + timezone.timedelta(days=7)
        )
    
    def test_invoice_creation(self):
        self.assertEqual(self.invoice.amount, Decimal('100.00'))
        self.assertEqual(self.invoice.status, Invoice.Status.NEW)
    
    def test_invoice_cancel(self):
        self.invoice.status = Invoice.Status.CANCELLED
        self.invoice.save()
        self.assertEqual(self.invoice.status, Invoice.Status.CANCELLED)
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from apps.core.models import Merchant, Project, Invoice, ExchangeRate
from apps.core.services import PaymentService, BalanceService


class BusinessLogicTest(TestCase):
    
    def setUp(self):
        self.merchant = Merchant.objects.create(name="Test Merchant")
        self.project = Project.objects.create(
            merchant=self.merchant,
            name="Test Project",
            api_key="test-key"
        )
        ExchangeRate.objects.create(
            from_currency="USD",
            to_currency="USD",
            rate=Decimal('1.000000'),
            timestamp=timezone.now()
        )

    def test_full_payment(self):
        """Полная оплата счета"""
        invoice = Invoice.objects.create(
            project=self.project,
            amount=Decimal('100.00'),
            currency="USD",
            external_id="INV-001",
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        PaymentService.process_payment(
            invoice_id=invoice.id,
            provider_transaction_id="txn-001",
            amount=Decimal('100.00'),
            currency="USD",
            received_at=timezone.now()
        )
        
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        
        balances = BalanceService.get_balance(self.merchant.id)
        self.assertEqual(balances.get('USD'), Decimal('99.00'))

    def test_partial_payment(self):
        """Частичная оплата"""
        invoice = Invoice.objects.create(
            project=self.project,
            amount=Decimal('100.00'),
            currency="USD",
            external_id="INV-002",
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        PaymentService.process_payment(
            invoice_id=invoice.id,
            provider_transaction_id="txn-002",
            amount=Decimal('60.00'),
            currency="USD",
            received_at=timezone.now()
        )
        
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PENDING)

    def test_minimum_fee(self):
        """Минимальная комиссия 0.50"""
        invoice = Invoice.objects.create(
            project=self.project,
            amount=Decimal('10.00'),
            currency="USD",
            external_id="INV-003",
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        PaymentService.process_payment(
            invoice_id=invoice.id,
            provider_transaction_id="txn-003",
            amount=Decimal('10.00'),
            currency="USD",
            received_at=timezone.now()
        )
        
        from apps.core.models import LedgerEntry
        fee = LedgerEntry.objects.get(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.FEE
        )
        self.assertEqual(fee.amount, Decimal('0.50'))
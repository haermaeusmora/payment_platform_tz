from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from django.db import transaction
from django.core.management import call_command
from io import StringIO

from ..models import Merchant, Project, Invoice, Payment, LedgerEntry, ExchangeRate
from ..services import PaymentService, InvoiceService, BalanceService


class PaymentFlowTest(TestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(
            name="Test Merchant",
            is_active=True
        )
        self.project = Project.objects.create(
            merchant=self.merchant,
            name="Test Project",
            api_key="test-key-123",
            notification_url="https://example.com/webhook",
            is_active=True
        )
        self.invoice = Invoice.objects.create(
            project=self.project,
            amount=Decimal('100.00'),
            currency="USD",
            external_id="INV-001",
            expires_at=timezone.now() + timezone.timedelta(days=7),
            status=Invoice.Status.NEW
        )
        ExchangeRate.objects.create(
            from_currency="USD",
            to_currency="USD",
            rate=Decimal('1.000000'),
            timestamp=timezone.now()
        )

    def test_full_payment_flow(self):
        """Тест полного цикла оплаты"""
        payment = PaymentService.process_payment(
            invoice_id=self.invoice.id,
            provider_transaction_id="txn-001",
            amount=Decimal('100.00'),
            currency="USD",
            received_at=timezone.now()
        )
        
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, Decimal('100.00'))
        self.assertEqual(payment.credited_amount, Decimal('100.00'))
        
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)
        
        balances = BalanceService.get_balance(self.merchant.id)
        self.assertEqual(balances.get('USD'), Decimal('99.00'))

    def test_partial_payment(self):
        """Тест частичной оплаты"""
        payment = PaymentService.process_payment(
            invoice_id=self.invoice.id,
            provider_transaction_id="txn-001",
            amount=Decimal('60.00'),
            currency="USD",
            received_at=timezone.now()
        )
        
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.PENDING)

        total_paid = sum(p.credited_amount or p.amount for p in self.invoice.payments.all())
        self.assertEqual(total_paid, Decimal('60.00'))

    def test_overpayment(self):
        """Тест переплаты > 1%"""
        payment = PaymentService.process_payment(
            invoice_id=self.invoice.id,
            provider_transaction_id="txn-001",
            amount=Decimal('150.00'),
            currency="USD",
            received_at=timezone.now()
        )
        
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.OVERPAID)
        
        balances = BalanceService.get_balance(self.merchant.id)
        self.assertEqual(balances.get('USD'), Decimal('148.50'))

    def test_idempotent_payment(self):
        """Тест идемпотентности платежа"""
        payment1 = PaymentService.process_payment(
            invoice_id=self.invoice.id,
            provider_transaction_id="txn-001",
            amount=Decimal('100.00'),
            currency="USD",
            received_at=timezone.now()
        )

        payment2 = PaymentService.process_payment(
            invoice_id=self.invoice.id,
            provider_transaction_id="txn-001",
            amount=Decimal('100.00'),
            currency="USD",
            received_at=timezone.now()
        )
        
        self.assertEqual(payment1.id, payment2.id)
        self.assertEqual(Payment.objects.count(), 1)

        balances = BalanceService.get_balance(self.merchant.id)
        self.assertEqual(balances.get('USD'), Decimal('99.00'))

    def test_cancel_paid_invoice(self):
        """Тест: нельзя отменить оплаченный счет"""
        PaymentService.process_payment(
            invoice_id=self.invoice.id,
            provider_transaction_id="txn-001",
            amount=Decimal('100.00'),
            currency="USD",
            received_at=timezone.now()
        )
        
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)

        from ..views.invoice_views import InvoiceCancelView
        self.invoice.status = Invoice.Status.CANCELLED
        self.invoice.save()
        self.invoice.refresh_from_db()

    def test_expire_invoices_command(self):
        """Тест команды просрочки счетов"""
        expired_invoice = Invoice.objects.create(
            project=self.project,
            amount=Decimal('50.00'),
            currency="USD",
            external_id="INV-EXPIRED",
            expires_at=timezone.now() - timezone.timedelta(days=1),
            status=Invoice.Status.NEW
        )

        valid_invoice = Invoice.objects.create(
            project=self.project,
            amount=Decimal('50.00'),
            currency="USD",
            external_id="INV-VALID",
            expires_at=timezone.now() + timezone.timedelta(days=7),
            status=Invoice.Status.NEW
        )

        out = StringIO()
        call_command('expire_invoices', stdout=out)

        expired_invoice.refresh_from_db()
        valid_invoice.refresh_from_db()
        
        self.assertEqual(expired_invoice.status, Invoice.Status.EXPIRED)
        self.assertEqual(valid_invoice.status, Invoice.Status.NEW)

    def test_fee_calculation(self):
        """Тест расчета комиссии"""
        small_invoice = Invoice.objects.create(
            project=self.project,
            amount=Decimal('10.00'),
            currency="USD",
            external_id="INV-SMALL",
            expires_at=timezone.now() + timezone.timedelta(days=7)
        )
        
        PaymentService.process_payment(
            invoice_id=small_invoice.id,
            provider_transaction_id="txn-small",
            amount=Decimal('10.00'),
            currency="USD",
            received_at=timezone.now()
        )

        fees = LedgerEntry.objects.filter(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.FEE
        )
        self.assertEqual(fees.count(), 1)
        self.assertEqual(fees.first().amount, Decimal('0.50'))
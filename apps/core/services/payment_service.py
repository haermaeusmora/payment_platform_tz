from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from ..models import Invoice, Payment, LedgerEntry, ExchangeRate
from .notification_service import NotificationService
from .rate_client import RateServiceClient


class PaymentService:
    FEE_PERCENT = Decimal('0.01')
    FEE_MIN = Decimal('0.50')
    OVERPAID_THRESHOLD = Decimal('0.01')

    @classmethod
    def process_payment(cls, invoice_id, provider_transaction_id, amount, currency, received_at):
        with transaction.atomic():
            try:
                existing_payment = Payment.objects.get(
                    provider_transaction_id=provider_transaction_id
                )
                return existing_payment
            except Payment.DoesNotExist:
                pass
            
            invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
            
            if invoice.status in [Invoice.Status.PAID, Invoice.Status.OVERPAID, Invoice.Status.EXPIRED, Invoice.Status.CANCELLED]:
                raise ValidationError(f"Cannot process payment for invoice in status {invoice.status}")

            payment = Payment.objects.create(
                invoice=invoice,
                amount=amount,
                currency=currency,
                provider_transaction_id=provider_transaction_id,
                received_at=received_at
            )

            credited_amount = cls._convert_currency(amount, currency, invoice.currency, received_at)
            payment.credited_amount = credited_amount
            payment.exchange_rate_used = cls._get_exchange_rate(currency, invoice.currency, received_at)
            payment.save()

            cls._create_ledger_entries(invoice, credited_amount, payment)

            cls._update_invoice_status(invoice)

        return payment
        
    @classmethod
    def _convert_currency(cls, amount, from_currency, to_currency, timestamp):
        if from_currency == to_currency:
            return amount
        
        rate = cls._get_exchange_rate(from_currency, to_currency, timestamp)
        if rate is None:
            raise ValidationError(f"No exchange rate found for {from_currency} to {to_currency}")
        
        return amount * rate

    @classmethod
    def _get_exchange_rate(cls, from_currency, to_currency, timestamp):
        """Получить курс валюты через сервис курсов"""
        if from_currency == to_currency:
            return Decimal('1.000000')
        
        rate = RateServiceClient.get_rate(from_currency, to_currency)
        
        if rate is not None:
            return rate

        try:
            rate_obj = ExchangeRate.objects.filter(
                from_currency=from_currency,
                to_currency=to_currency,
                timestamp__lte=timestamp
            ).order_by('-timestamp').first()
            
            if rate_obj:
                return rate_obj.rate
            return None
        except ExchangeRate.DoesNotExist:
            return None

    @classmethod
    def _create_ledger_entries(cls, invoice, credited_amount, payment):
        merchant = invoice.project.merchant
        
        deposit = LedgerEntry.objects.create(
            merchant=merchant,
            invoice=invoice,
            payment=payment,
            entry_type=LedgerEntry.EntryType.DEPOSIT,
            amount=credited_amount,
            currency=invoice.currency,
            description=f"Payment for invoice {invoice.external_id}"
        )

        fee = cls._calculate_fee(credited_amount, invoice.currency)
        if fee > 0:
            LedgerEntry.objects.create(
                merchant=merchant,
                invoice=invoice,
                payment=payment,
                entry_type=LedgerEntry.EntryType.FEE,
                amount=fee,
                currency=invoice.currency,
                fee_percent=cls.FEE_PERCENT * 100,
                fee_min_amount=cls.FEE_MIN,
                description=f"Fee for invoice {invoice.external_id}"
            )

    @classmethod
    def _calculate_fee(cls, amount, currency):
        fee = amount * cls.FEE_PERCENT
        if fee < cls.FEE_MIN:
            fee = cls.FEE_MIN
        return fee

    @classmethod
    def _update_invoice_status(cls, invoice):
        total_paid = sum(p.credited_amount or p.amount for p in invoice.payments.all())
        
        if total_paid >= invoice.amount:
            overpaid = total_paid - invoice.amount
            if overpaid > invoice.amount * cls.OVERPAID_THRESHOLD:
                invoice.status = Invoice.Status.OVERPAID
            else:
                invoice.status = Invoice.Status.PAID
        else:
            if timezone.now() > invoice.expires_at:
                invoice.status = Invoice.Status.UNDERPAID
            else:
                invoice.status = Invoice.Status.PENDING
        
        invoice.save()

        if invoice.status in [Invoice.Status.PAID, Invoice.Status.OVERPAID, Invoice.Status.UNDERPAID, Invoice.Status.EXPIRED]:
            from .notification_service import NotificationService
            NotificationService.create_notification(invoice)
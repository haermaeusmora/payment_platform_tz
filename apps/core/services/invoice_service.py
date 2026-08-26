from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from ..models import Invoice


class InvoiceService:
    @staticmethod
    def create_invoice(project, external_id, amount, currency, expires_at, description=''):
        amount = Decimal(str(amount))
        
        if amount <= 0:
            raise ValueError('Amount must be greater than 0')
        
        invoice, created = Invoice.objects.get_or_create(
            project=project,
            external_id=external_id,
            defaults={
                'amount': amount,
                'currency': currency,
                'expires_at': expires_at,
                'description': description,
                'status': Invoice.Status.NEW
            }
        )
        
        return invoice
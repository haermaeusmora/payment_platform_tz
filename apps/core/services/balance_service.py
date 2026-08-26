from decimal import Decimal
from django.db.models import Sum
from ..models import LedgerEntry


class BalanceService:
    @classmethod
    def get_balance(cls, merchant_id):
        entries = LedgerEntry.objects.filter(merchant_id=merchant_id)
        
        balances = {}
        currencies = entries.values_list('currency', flat=True).distinct()
        
        for currency in currencies:
            deposits = entries.filter(
                entry_type=LedgerEntry.EntryType.DEPOSIT,
                currency=currency
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            fees = entries.filter(
                entry_type=LedgerEntry.EntryType.FEE,
                currency=currency
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            balances[currency] = deposits - fees
        
        return balances
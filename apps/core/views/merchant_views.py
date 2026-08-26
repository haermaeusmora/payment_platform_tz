from django.http import JsonResponse
from django.views import View
from django.db.models import Count, Sum, Q
from decimal import Decimal
from ..models import Merchant, Invoice, LedgerEntry
from ..services.balance_service import BalanceService


class MerchantBalanceView(View):
    def get(self, request, pk):
        try:
            merchant = Merchant.objects.get(pk=pk)
        except Merchant.DoesNotExist:
            return JsonResponse(
                {'error': 'Merchant not found'},
                status=404
            )

        balances = BalanceService.get_balance(pk)
        
        return JsonResponse({
            'merchant_id': merchant.id,
            'merchant_name': merchant.name,
            'balances': balances
        })


class MerchantReportView(View):
    def get(self, request, pk):
        try:
            merchant = Merchant.objects.get(pk=pk)
        except Merchant.DoesNotExist:
            return JsonResponse(
                {'error': 'Merchant not found'},
                status=404
            )

        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        group_by = request.GET.get('group_by', 'day')

        if not date_from or not date_to:
            return JsonResponse(
                {'error': 'date_from and date_to are required'},
                status=400
            )

        invoices = Invoice.objects.filter(
            project__merchant_id=pk,
            created_at__date__gte=date_from,
            created_at__date__lte=date_to
        )

        if group_by == 'project':
            result = self._group_by_project(invoices)
        else:
            result = self._group_by_day(invoices)

        return JsonResponse(result)

    def _group_by_day(self, invoices):
        from django.db.models.functions import TruncDate
        
        grouped = invoices.annotate(
            day=TruncDate('created_at')
        ).values('day').annotate(
            total_invoices=Count('id'),
            paid_invoices=Count('id', filter=Q(status__in=[Invoice.Status.PAID, Invoice.Status.OVERPAID])),
            total_amount=Sum('amount'),
            total_received=Sum('payments__credited_amount'),
            total_fee=Sum('ledger_entries__amount', filter=Q(ledger_entries__entry_type=LedgerEntry.EntryType.FEE))
        ).order_by('day')

        result = []
        for item in grouped:
            total_received = item['total_received'] or Decimal('0.00')
            total_amount = item['total_amount'] or Decimal('0.00')
            conversion = (total_received / total_amount * 100) if total_amount > 0 else Decimal('0.00')
            
            result.append({
                'date': item['day'].isoformat(),
                'total_invoices': item['total_invoices'],
                'paid_invoices': item['paid_invoices'],
                'total_amount': str(total_amount),
                'total_received': str(total_received),
                'total_fee': str(item['total_fee'] or Decimal('0.00')),
                'conversion_rate': str(conversion)
            })

        return {'group_by': 'day', 'data': result}

    def _group_by_project(self, invoices):
        grouped = invoices.values(
            'project__id',
            'project__name'
        ).annotate(
            total_invoices=Count('id'),
            paid_invoices=Count('id', filter=Q(status__in=[Invoice.Status.PAID, Invoice.Status.OVERPAID])),
            total_amount=Sum('amount'),
            total_received=Sum('payments__credited_amount'),
            total_fee=Sum('ledger_entries__amount', filter=Q(ledger_entries__entry_type=LedgerEntry.EntryType.FEE))
        ).order_by('project__name')

        result = []
        for item in grouped:
            total_received = item['total_received'] or Decimal('0.00')
            total_amount = item['total_amount'] or Decimal('0.00')
            conversion = (total_received / total_amount * 100) if total_amount > 0 else Decimal('0.00')
            
            result.append({
                'project_id': item['project__id'],
                'project_name': item['project__name'],
                'total_invoices': item['total_invoices'],
                'paid_invoices': item['paid_invoices'],
                'total_amount': str(total_amount),
                'total_received': str(total_received),
                'total_fee': str(item['total_fee'] or Decimal('0.00')),
                'conversion_rate': str(conversion)
            })

        return {'group_by': 'project', 'data': result}
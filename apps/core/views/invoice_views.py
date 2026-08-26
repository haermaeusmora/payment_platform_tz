import json
from decimal import Decimal
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db import transaction
from ..models import Invoice, Project
from ..services import InvoiceService


@method_decorator(csrf_exempt, name='dispatch')
class InvoiceCreateView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {'error': 'Invalid JSON'},
                status=400
            )

        api_key = request.headers.get('X-Api-Key')
        if not api_key:
            return JsonResponse(
                {'error': 'X-Api-Key header required'},
                status=401
            )

        try:
            project = Project.objects.get(api_key=api_key, is_active=True)
        except Project.DoesNotExist:
            return JsonResponse(
                {'error': 'Invalid API key'},
                status=401
            )

        required_fields = ['external_id', 'amount', 'currency', 'expires_at']
        for field in required_fields:
            if field not in data:
                return JsonResponse(
                    {'error': f'Field {field} is required'},
                    status=400
                )

        try:
            amount = Decimal(str(data['amount']))
            if amount <= 0:
                raise ValueError('Amount must be greater than 0')
        except (ValueError, TypeError):
            return JsonResponse(
                {'error': 'Invalid amount format'},
                status=400
            )

        try:
            invoice = InvoiceService.create_invoice(
                project=project,
                external_id=data['external_id'],
                amount=amount,
                currency=data['currency'],
                expires_at=data['expires_at'],
                description=data.get('description', '')
            )
            return JsonResponse({
                'id': invoice.id,
                'external_id': invoice.external_id,
                'amount': str(invoice.amount),
                'currency': invoice.currency,
                'status': invoice.status,
                'created_at': invoice.created_at.isoformat(),
                'expires_at': invoice.expires_at.isoformat()
            }, status=201)
        except Exception as e:
            return JsonResponse(
                {'error': str(e)},
                status=400
            )


class InvoiceDetailView(View):
    def get(self, request, pk):
        try:
            invoice = Invoice.objects.select_related('project__merchant').prefetch_related('payments').get(pk=pk)
        except Invoice.DoesNotExist:
            return JsonResponse(
                {'error': 'Invoice not found'},
                status=404
            )

        total_paid = sum(p.credited_amount or p.amount for p in invoice.payments.all())
        remaining = invoice.amount - total_paid if total_paid < invoice.amount else Decimal('0.00')

        return JsonResponse({
            'id': invoice.id,
            'external_id': invoice.external_id,
            'amount': str(invoice.amount),
            'currency': invoice.currency,
            'status': invoice.status,
            'created_at': invoice.created_at.isoformat(),
            'expires_at': invoice.expires_at.isoformat(),
            'description': invoice.description,
            'project': {
                'id': invoice.project.id,
                'name': invoice.project.name,
                'merchant': invoice.project.merchant.name
            },
            'payments': [
                {
                    'id': p.id,
                    'amount': str(p.amount),
                    'currency': p.currency,
                    'provider_transaction_id': p.provider_transaction_id,
                    'received_at': p.received_at.isoformat()
                } for p in invoice.payments.all()
            ],
            'total_paid': str(total_paid),
            'remaining': str(remaining)
        })


@method_decorator(csrf_exempt, name='dispatch')
class InvoiceCancelView(View):
    def post(self, request, pk):
        try:
            invoice = Invoice.objects.get(pk=pk)
        except Invoice.DoesNotExist:
            return JsonResponse(
                {'error': 'Invoice not found'},
                status=404
            )

        if invoice.status in [Invoice.Status.PAID, Invoice.Status.OVERPAID]:
            return JsonResponse(
                {'error': 'Cannot cancel paid invoice'},
                status=400
            )

        invoice.status = Invoice.Status.CANCELLED
        invoice.save()

        return JsonResponse({
            'id': invoice.id,
            'status': invoice.status,
            'message': 'Invoice cancelled successfully'
        })
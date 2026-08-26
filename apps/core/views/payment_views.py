import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.utils import timezone
from ..services import PaymentService


@method_decorator(csrf_exempt, name='dispatch')
class PaymentWebhookView(View):
    def post(self, request):
        api_key = request.headers.get('X-Internal-Key')
        
        if api_key != settings.INTERNAL_API_KEY:
            return JsonResponse(
                {'error': 'Invalid internal API key'},
                status=401
            )

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {'error': 'Invalid JSON'},
                status=400
            )

        required_fields = ['invoice_id', 'provider_transaction_id', 'amount', 'currency', 'received_at']
        for field in required_fields:
            if field not in data:
                return JsonResponse(
                    {'error': f'Field {field} is required'},
                    status=400
                )

        try:
            payment = PaymentService.process_payment(
                invoice_id=data['invoice_id'],
                provider_transaction_id=data['provider_transaction_id'],
                amount=data['amount'],
                currency=data['currency'],
                received_at=data['received_at']
            )
            
            return JsonResponse({
                'id': payment.id,
                'invoice_id': payment.invoice_id,
                'provider_transaction_id': payment.provider_transaction_id,
                'amount': str(payment.amount),
                'currency': payment.currency,
                'credited_amount': str(payment.credited_amount),
                'status': 'processed'
            }, status=201)
            
        except Exception as e:
            return JsonResponse(
                {'error': str(e)},
                status=400
            )
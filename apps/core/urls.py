from django.urls import path
from .views.invoice_views import InvoiceCreateView, InvoiceDetailView, InvoiceCancelView
from .views.payment_views import PaymentWebhookView
from .views.merchant_views import MerchantBalanceView, MerchantReportView

urlpatterns = [
    path('invoices/', InvoiceCreateView.as_view(), name='invoice-create'),
    path('invoices/<int:pk>/', InvoiceDetailView.as_view(), name='invoice-detail'),
    path('invoices/<int:pk>/cancel/', InvoiceCancelView.as_view(), name='invoice-cancel'),
    path('internal/payments/', PaymentWebhookView.as_view(), name='payment-webhook'),
    path('merchants/<int:pk>/balance/', MerchantBalanceView.as_view(), name='merchant-balance'),
    path('merchants/<int:pk>/report/', MerchantReportView.as_view(), name='merchant-report'),
]
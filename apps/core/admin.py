from django.contrib import admin
from .models import Merchant, Project, Invoice, Payment, LedgerEntry, ExchangeRate, Notification


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'merchant', 'name', 'api_key', 'is_active', 'created_at')
    list_filter = ('is_active', 'merchant')
    search_fields = ('name', 'api_key')
    raw_id_fields = ('merchant',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'external_id', 'project', 'amount', 'currency', 'status', 'created_at', 'expires_at')
    list_filter = ('status', 'currency', 'project')
    search_fields = ('external_id',)
    raw_id_fields = ('project',)
    readonly_fields = ('created_at',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'provider_transaction_id', 'invoice', 'amount', 'currency', 'received_at')
    list_filter = ('currency',)
    search_fields = ('provider_transaction_id',)
    raw_id_fields = ('invoice',)


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'merchant', 'entry_type', 'amount', 'currency', 'created_at')
    list_filter = ('entry_type', 'currency')
    raw_id_fields = ('merchant', 'invoice', 'payment')


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('from_currency', 'to_currency', 'rate', 'timestamp')
    list_filter = ('from_currency', 'to_currency')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'invoice', 'status', 'attempt_count', 'created_at')
    list_filter = ('status',)
    raw_id_fields = ('invoice', 'project')
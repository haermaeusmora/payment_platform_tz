from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator


class Merchant(models.Model):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Project(models.Model):
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name='projects'
    )
    name = models.CharField(max_length=255)
    api_key = models.CharField(max_length=64, unique=True)
    notification_url = models.URLField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.merchant.name} — {self.name}"


class Invoice(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'New'
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        UNDERPAID = 'underpaid', 'Underpaid'
        OVERPAID = 'overpaid', 'Overpaid'
        EXPIRED = 'expired', 'Expired'
        CANCELLED = 'cancelled', 'Cancelled'

    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name='invoices'
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3)
    external_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True
    )
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [('project', 'external_id')]
        indexes = [
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['project', 'status']),
            models.Index(fields=['project', 'created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='invoice_amount_positive'
            )
        ]

    def __str__(self):
        return f"Invoice {self.external_id} ({self.currency} {self.amount})"

    def send_notification(self):
        from .services.notification_service import NotificationService
        
        if self.status in [self.Status.PAID, self.Status.OVERPAID, self.Status.UNDERPAID, self.Status.EXPIRED]:
            return NotificationService.create_notification(self)
        return None

class Payment(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3)
    provider_transaction_id = models.CharField(max_length=255, unique=True)
    received_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    exchange_rate_used = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True
    )
    credited_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=['invoice', 'received_at']),
        ]

    def __str__(self):
        return f"Payment {self.provider_transaction_id}"


class LedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        DEPOSIT = 'deposit', 'Deposit'
        FEE = 'fee', 'Fee'

    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.PROTECT,
        related_name='ledger_entries'
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='ledger_entries'
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='ledger_entries'
    )
    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.CharField(max_length=3)
    fee_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    fee_min_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['merchant', 'currency']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.entry_type} {self.amount} {self.currency}"


class ExchangeRate(models.Model):
    from_currency = models.CharField(max_length=3)
    to_currency = models.CharField(max_length=3)
    rate = models.DecimalField(max_digits=20, decimal_places=6)
    timestamp = models.DateTimeField()

    class Meta:
        unique_together = [('from_currency', 'to_currency', 'timestamp')]
        indexes = [
            models.Index(fields=['from_currency', 'to_currency', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.from_currency}/{self.to_currency} = {self.rate} at {self.timestamp}"


class Notification(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'
        RETRY = 'retry', 'Retry'
        EXPIRED = 'expired', 'Expired'

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='notifications'
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name='notifications'
    )
    url = models.URLField(max_length=500)
    payload = models.JSONField()
    signature = models.CharField(max_length=128)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    attempt_count = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True, db_index=True)
    response_status = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'next_retry_at']),
            models.Index(fields=['invoice', 'status']),
        ]

    def __str__(self):
        return f"Notification for {self.invoice} ({self.status})"

    def is_terminal(self):
        return self.status in (self.Status.SENT, self.Status.EXPIRED)

    def can_retry(self):
        return (
            self.status in (self.Status.FAILED, self.Status.RETRY)
            and self.attempt_count < self.max_attempts
        )
from django.db import models
from django.conf import settings


CREDIT_COSTS = {
    'generate': 1,
    'publish': 0,
}


class CreditTransaction(models.Model):
    USE = 'use'
    ADD = 'add'
    REFUND = 'refund'

    TYPE_CHOICES = [
        (USE, 'Penggunaan'),
        (ADD, 'Penambahan'),
        (REFUND, 'Refund'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    job = models.ForeignKey('queue_manager.QueueJob', on_delete=models.SET_NULL, null=True, blank=True)
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.IntegerField()
    description = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.amount > 0 else ''
        return f"{self.user.email} {sign}{self.amount} — {self.description}"


class CreditPackage(models.Model):
    """A buyable bundle of credits — populated by `manage.py seed_packages`."""

    name = models.CharField(max_length=100)
    credits = models.PositiveIntegerField()
    price_idr = models.PositiveIntegerField(help_text='Harga dalam Rupiah.')
    is_popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'credits']

    def __str__(self):
        return f"{self.name} — {self.credits} kredit · Rp{self.price_idr:,}"

    @property
    def price_per_credit(self):
        return round(self.price_idr / self.credits, 2) if self.credits else 0


class Payment(models.Model):
    """One top-up attempt. Confirmed payments add credits via billing.credits.add_credits."""

    PENDING = 'pending'
    PAID = 'paid'
    FAILED = 'failed'
    EXPIRED = 'expired'

    STATUS_CHOICES = [
        (PENDING, 'Menunggu'),
        (PAID, 'Berhasil'),
        (FAILED, 'Gagal'),
        (EXPIRED, 'Kadaluarsa'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    package = models.ForeignKey(CreditPackage, on_delete=models.PROTECT, related_name='payments')

    provider = models.CharField(max_length=30, help_text="e.g. 'mock' or 'mayar'")
    provider_ref = models.CharField(max_length=200, blank=True, help_text='Reference id at the provider.')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)

    amount_idr = models.PositiveIntegerField()
    credits_granted = models.PositiveIntegerField(default=0)
    pay_url = models.URLField(blank=True, max_length=1000)
    raw = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment#{self.pk} {self.user.email} {self.amount_idr} ({self.status})"

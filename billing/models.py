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

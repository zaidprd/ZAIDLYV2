"""Mock payment provider — instant 'paid' simulation for dev/demo (no real money).

The user is redirected to a local confirm page that POSTs back to mark the payment
as paid and grant credits. Lets the full top-up flow work end-to-end before
Mayar.id credentials exist.
"""
import secrets

from django.urls import reverse

from .base import PaymentProvider, Invoice


class MockPaymentProvider(PaymentProvider):
    name = "mock"

    def create_invoice(self, payment) -> Invoice:
        ref = f"mock-{secrets.token_hex(8)}"
        return Invoice(
            pay_url=reverse('payment_mock_confirm', args=[payment.pk]),
            provider_ref=ref,
            raw={'note': 'Mock provider — no real payment.'},
        )

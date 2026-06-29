"""Mayar.id payment provider — real invoice + webhook.

Stays inert until MAYAR_API_KEY is set; selecting `PAYMENT_PROVIDER=mayar` then
makes top-up live without any other code change.
"""
import requests
from decouple import config

from .base import PaymentProvider, Invoice


class MayarPaymentProvider(PaymentProvider):
    name = "mayar"

    def create_invoice(self, payment) -> Invoice:
        api_key = config('MAYAR_API_KEY')
        callback = config('MAYAR_CALLBACK_URL', default='')
        resp = requests.post(
            'https://api.mayar.id/hl/v1/payment/create',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'name': payment.package.name,
                'amount': payment.amount_idr,
                'mobile': '',
                'email': payment.user.email,
                'description': f'Top-up {payment.package.credits} kredit SEO.Zaidly',
                'redirectUrl': callback,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get('data') or {}
        return Invoice(
            pay_url=data.get('link', ''),
            provider_ref=str(data.get('id') or data.get('transactionId') or ''),
            raw=data,
        )

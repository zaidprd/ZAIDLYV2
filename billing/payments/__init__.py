"""Payment provider seam. Pick via PAYMENT_PROVIDER (default: mock).

Switching providers (mock -> mayar -> midtrans, etc.) is purely a config change.
The app only ever talks to PaymentProvider.create_invoice().
"""
from decouple import config

from .base import PaymentProvider, Invoice


def get_provider() -> PaymentProvider:
    name = config('PAYMENT_PROVIDER', default='mock')
    if name == 'mock':
        from .mock import MockPaymentProvider
        return MockPaymentProvider()
    if name == 'mayar':
        from .mayar import MayarPaymentProvider
        return MayarPaymentProvider()
    raise ValueError(f"Unknown PAYMENT_PROVIDER: {name!r}")


__all__ = ['PaymentProvider', 'Invoice', 'get_provider']

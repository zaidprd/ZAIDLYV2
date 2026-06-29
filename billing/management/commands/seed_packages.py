"""Idempotent seed for the default credit packages.

Pricing aims for ~60-70% margin on a $0.30/credit selling price (4500 IDR @ 15k).
Adjust per market; the command is safe to re-run.
"""
from django.core.management.base import BaseCommand

from billing.models import CreditPackage


DEFAULT_PACKAGES = [
    {'name': 'Starter',  'credits': 10,  'price_idr':  49_000, 'is_popular': False, 'sort_order': 1},
    {'name': 'Growth',   'credits': 50,  'price_idr': 199_000, 'is_popular': True,  'sort_order': 2},
    {'name': 'Pro',      'credits': 150, 'price_idr': 499_000, 'is_popular': False, 'sort_order': 3},
    {'name': 'Business', 'credits': 500, 'price_idr':1_490_000, 'is_popular': False, 'sort_order': 4},
]


class Command(BaseCommand):
    help = "Seed (or update) the default CreditPackage rows."

    def handle(self, *args, **opts):
        for data in DEFAULT_PACKAGES:
            pkg, created = CreditPackage.objects.update_or_create(
                name=data['name'], defaults=data,
            )
            verb = 'created' if created else 'updated'
            self.stdout.write(f"  {verb}: {pkg}")
        self.stdout.write(self.style.SUCCESS(f"Selesai. {CreditPackage.objects.filter(is_active=True).count()} paket aktif."))

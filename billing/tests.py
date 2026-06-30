"""Billing flow: package list -> checkout -> mock confirm -> credits granted."""
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from billing.models import CreditPackage, Payment


class BillingFlowTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='b', password='pw12345678', email='b@b.com')
        self.u.credits = 0
        self.u.save()
        self.client.force_login(self.u)
        self.pkg = CreditPackage.objects.create(name='Starter', credits=10, price_idr=49000, sort_order=1)

    def test_package_list_renders(self):
        resp = self.client.get(reverse('package_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Starter')

    def test_checkout_creates_pending_payment_and_redirects_to_pay_url(self):
        resp = self.client.post(reverse('package_checkout', args=[self.pkg.pk]))
        self.assertEqual(resp.status_code, 302)
        p = Payment.objects.get(user=self.u, package=self.pkg)
        self.assertEqual(p.status, Payment.PENDING)
        self.assertTrue(p.pay_url)                                          # provider returned a URL
        self.assertEqual(resp.url, p.pay_url)

    def test_mock_confirm_grants_credits_and_is_idempotent(self):
        self.client.post(reverse('package_checkout', args=[self.pkg.pk]))
        p = Payment.objects.get(user=self.u)
        self.client.post(reverse('payment_mock_confirm', args=[p.pk]))
        self.u.refresh_from_db(); p.refresh_from_db()
        self.assertEqual(self.u.credits, 10)
        self.assertEqual(p.status, Payment.PAID)
        self.assertEqual(p.credits_granted, 10)
        # Re-posting must NOT double-credit (idempotent).
        self.client.post(reverse('payment_mock_confirm', args=[p.pk]))
        self.u.refresh_from_db()
        self.assertEqual(self.u.credits, 10)

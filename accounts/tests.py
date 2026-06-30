"""Auth + Threads connect flow (mock mode, no Threads app configured)."""
from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class ProfileAndThreadsTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='p', password='pw12345678', email='p@p.com')
        self.client.force_login(self.u)

    def test_profile_page_renders(self):
        resp = self.client.get(reverse('profile'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Threads')

    def test_threads_connect_demo_mode(self):
        resp = self.client.get(reverse('threads_connect'))
        self.assertRedirects(resp, reverse('profile'))
        self.u.refresh_from_db()
        self.assertTrue(self.u.threads_user_id)
        self.assertTrue(self.u.threads_access_token)

    def test_threads_disconnect(self):
        self.u.threads_user_id = 'x'
        self.u.threads_access_token = 'y'
        self.u.save()
        resp = self.client.post(reverse('threads_disconnect'))
        self.assertRedirects(resp, reverse('profile'))
        self.u.refresh_from_db()
        self.assertEqual(self.u.threads_user_id, '')
        self.assertEqual(self.u.threads_access_token, '')

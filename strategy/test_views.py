"""Campaign UI view tests.

Memverifikasi gate Business Profile + bahwa Start AI Campaign mengantrekan task
ke django_q tanpa benar-benar memanggil AI (mock async_task).
"""
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from projects.models import Project
from strategy.models import Campaign


def _make_project(user, **kw):
    return Project.objects.create(user=user, name=kw.pop('name', 'P'), language='id', **kw)


class CampaignViewsTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='c', password='pw12345678', email='c@c.com')
        self.client.force_login(self.u)

    def test_list_renders_when_empty(self):
        resp = self.client.get(reverse('campaign_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Mulai AI Campaign')

    def test_start_blocked_without_business_profile(self):
        project = _make_project(self.u, business_description='', niche='')
        with mock.patch('strategy.campaign.async_task') as mocked:
            resp = self.client.post(reverse('campaign_start_ai', args=[project.pk]), follow=True)
        # Gate harus mencegah trigger engine
        mocked.assert_not_called()
        self.assertEqual(Campaign.objects.count(), 0)
        self.assertContains(resp, 'Lengkapi Business Profile')

    def test_start_ai_campaign_enqueues_and_redirects(self):
        project = _make_project(self.u, business_description='Jual panel listrik', niche='panel listrik')
        with mock.patch('strategy.campaign.async_task') as mocked:
            resp = self.client.post(reverse('campaign_start_ai', args=[project.pk]),
                                    {'articles_per_day': '5'})
        campaign = Campaign.objects.get(project=project)
        self.assertEqual(campaign.status, 'building')
        self.assertEqual(campaign.articles_per_day, 5)
        self.assertEqual(campaign.mode, 'ai')
        mocked.assert_called_once()
        # task name + campaign id sebagai first arg
        self.assertEqual(mocked.call_args.args[0], 'strategy.tasks.run_build_ai_campaign')
        self.assertEqual(mocked.call_args.args[1], campaign.id)
        self.assertRedirects(resp, reverse('campaign_detail', args=[campaign.pk]))

    def test_detail_and_status_poll(self):
        project = _make_project(self.u, business_description='X', niche='x')
        campaign = Campaign.objects.create(project=project, name='Camp', mode='ai',
                                            status='building', progress_step='analyzing')
        detail = self.client.get(reverse('campaign_detail', args=[campaign.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, 'Camp')
        self.assertContains(detail, 'Analisa bisnis')
        # HTMX polling endpoint
        poll = self.client.get(reverse('campaign_status_poll', args=[campaign.pk]))
        self.assertEqual(poll.status_code, 200)
        self.assertContains(poll, 'campaign-status')

    def test_approve_blocked_when_not_plan_ready(self):
        project = _make_project(self.u, business_description='X', niche='x')
        campaign = Campaign.objects.create(project=project, mode='ai', status='building')
        with mock.patch('strategy.views.start_campaign') as starter, \
             mock.patch('strategy.views.run_campaign_tick') as ticker:
            resp = self.client.post(reverse('campaign_approve', args=[campaign.pk]), follow=True)
        starter.assert_not_called()
        ticker.assert_not_called()
        self.assertContains(resp, 'belum siap')

    def test_approve_starts_running_and_drips(self):
        project = _make_project(self.u, business_description='X', niche='x')
        campaign = Campaign.objects.create(project=project, mode='ai', status='plan_ready',
                                            articles_per_day=3)
        with mock.patch('strategy.views.start_campaign') as starter, \
             mock.patch('strategy.views.run_campaign_tick') as ticker:
            resp = self.client.post(reverse('campaign_approve', args=[campaign.pk]))
        starter.assert_called_once_with(campaign)
        ticker.assert_called_once_with(campaign)         # first drip immediately
        self.assertRedirects(resp, reverse('campaign_detail', args=[campaign.pk]))

    def test_user_cannot_see_others_campaign(self):
        other = User.objects.create_user(username='o', password='pw12345678', email='o@o.com')
        project = _make_project(other, business_description='X', niche='x')
        campaign = Campaign.objects.create(project=project, mode='ai')
        resp = self.client.get(reverse('campaign_detail', args=[campaign.pk]))
        self.assertEqual(resp.status_code, 404)

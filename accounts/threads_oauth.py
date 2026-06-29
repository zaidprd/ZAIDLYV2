"""Threads OAuth — real token exchange (only used when THREADS_APP_* are set).

The connect flow falls back to a demo connection when no Threads app is
configured (see accounts.views.threads_connect), so the feature is usable now and
becomes real OAuth the moment credentials are added — no code change.
"""
import requests
from decouple import config


def is_configured():
    return bool(config('THREADS_APP_ID', default='') and config('THREADS_REDIRECT_URI', default=''))


def authorize_url():
    app_id = config('THREADS_APP_ID', default='')
    redirect_uri = config('THREADS_REDIRECT_URI', default='')
    scope = 'threads_basic,threads_content_publish'
    return ('https://threads.net/oauth/authorize'
            f'?client_id={app_id}&redirect_uri={redirect_uri}&scope={scope}&response_type=code')


def exchange_code(code):
    """Exchange an authorization code for (access_token, user_id)."""
    app_id = config('THREADS_APP_ID')
    secret = config('THREADS_APP_SECRET')
    redirect_uri = config('THREADS_REDIRECT_URI')
    resp = requests.post(
        'https://graph.threads.net/oauth/access_token',
        data={'client_id': app_id, 'client_secret': secret, 'grant_type': 'authorization_code',
              'redirect_uri': redirect_uri, 'code': code},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data['access_token']
    user_id = str(data.get('user_id') or '')
    if not user_id:
        me = requests.get('https://graph.threads.net/v1.0/me',
                          params={'fields': 'id', 'access_token': token}, timeout=30)
        me.raise_for_status()
        user_id = str(me.json()['id'])
    return token, user_id

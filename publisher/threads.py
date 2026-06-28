import requests


def post_to_threads(user_id, access_token, text):
    base = 'https://graph.threads.net/v1.0'

    # Step 1: create container
    container = requests.post(
        f"{base}/{user_id}/threads",
        params={
            'media_type': 'TEXT',
            'text': text,
            'access_token': access_token,
        },
        timeout=30,
    )
    container.raise_for_status()
    creation_id = container.json()['id']

    # Step 2: publish
    publish = requests.post(
        f"{base}/{user_id}/threads_publish",
        params={
            'creation_id': creation_id,
            'access_token': access_token,
        },
        timeout=30,
    )
    publish.raise_for_status()
    return publish.json().get('id', '')


def build_threads_text(title, url, keyword):
    return f"{title}\n\n{url}\n\n#{keyword.replace(' ', '')}"

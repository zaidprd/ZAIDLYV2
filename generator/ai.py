import requests
from decouple import config


def call_ai(messages, model=None, temperature=0.7, max_tokens=4000):
    api_key = config('AI_API_KEY', default='')
    base_url = config('AI_BASE_URL', default='https://api.openai.com/v1').rstrip('/')
    if not model:
        model = config('AI_DEFAULT_MODEL', default='gpt-4o-mini')

    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()['choices'][0]['message']['content'].strip()


def generate_image(prompt):
    api_key = config('AI_API_KEY', default='')
    base_url = config('AI_BASE_URL', default='https://api.openai.com/v1').rstrip('/')
    model = config('AI_IMAGE_MODEL', default='')

    if not model:
        return ''

    resp = requests.post(
        f"{base_url}/images/generations",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data['data'][0].get('url', '')

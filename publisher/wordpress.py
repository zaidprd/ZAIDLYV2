import requests


class WordPressClient:
    def __init__(self, site):
        self.base = site.url
        self.auth = (site.username, site.app_password)

    def _post(self, endpoint, data):
        resp = requests.post(
            f"{self.base}/wp-json/wp/v2/{endpoint}",
            auth=self.auth,
            json=data,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def upload_image(self, image_url, filename='featured.jpg', alt_text=''):
        img_resp = requests.get(image_url, timeout=30)
        img_resp.raise_for_status()

        resp = requests.post(
            f"{self.base}/wp-json/wp/v2/media",
            auth=self.auth,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': img_resp.headers.get('Content-Type', 'image/jpeg'),
            },
            data=img_resp.content,
            timeout=60,
        )
        resp.raise_for_status()
        media_id = resp.json()['id']

        # Set alt text (and title) on the media object — a second call is required
        # because the binary upload can't carry JSON fields.
        if alt_text:
            self._post(f'media/{media_id}', {'alt_text': alt_text, 'title': alt_text})
        return media_id

    def publish_post(self, title, content, slug, meta_description, status='publish',
                     featured_media_id=None, meta_title=''):
        data = {
            'title': title,
            'content': content,
            'slug': slug,
            'status': status,
            'excerpt': meta_description,
        }
        if featured_media_id:
            data['featured_media'] = featured_media_id

        # Yoast SEO / RankMath meta via custom fields (basic; works when meta keys are
        # exposed via REST — no plugin install assumed).
        meta = {}
        if meta_description:
            meta['_yoast_wpseo_metadesc'] = meta_description
            meta['rank_math_description'] = meta_description
        if meta_title:
            meta['_yoast_wpseo_title'] = meta_title
            meta['rank_math_title'] = meta_title
        if meta:
            data['meta'] = meta

        post = self._post('posts', data)
        return {
            'wp_post_id': post['id'],
            'wp_post_url': post['link'],
            'wp_status': post['status'],
        }

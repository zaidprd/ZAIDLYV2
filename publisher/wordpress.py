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

    def upload_image(self, image_url, filename='featured.jpg'):
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
        return resp.json()['id']

    def publish_post(self, title, content, slug, meta_description, status='publish', featured_media_id=None):
        data = {
            'title': title,
            'content': content,
            'slug': slug,
            'status': status,
            'excerpt': meta_description,
        }
        if featured_media_id:
            data['featured_media'] = featured_media_id

        # Yoast SEO / RankMath meta via custom fields if available
        if meta_description:
            data['meta'] = {
                '_yoast_wpseo_metadesc': meta_description,
                'rank_math_description': meta_description,
            }

        post = self._post('posts', data)
        return {
            'wp_post_id': post['id'],
            'wp_post_url': post['link'],
            'wp_status': post['status'],
        }

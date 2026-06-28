from .wordpress import WordPressClient
from .threads import post_to_threads, build_threads_text


def run_publish_wordpress(job_id):
    from queue_manager.models import QueueJob

    try:
        job = QueueJob.objects.select_related('project', 'site', 'user').get(pk=job_id)
    except QueueJob.DoesNotExist:
        return

    if not job.site:
        job.mark_failed('Tidak ada WordPress site yang dikonfigurasi untuk job ini.')
        return

    job.mark_processing()

    try:
        result = dict(job.result)
        client = WordPressClient(job.site)

        # Upload featured image if available
        featured_media_id = None
        if result.get('image_url'):
            try:
                featured_media_id = client.upload_image(result['image_url'])
            except Exception:
                pass

        # Publish post
        wp_result = client.publish_post(
            title=job.title,
            content=result.get('article_html', ''),
            slug=result.get('slug', ''),
            meta_description=result.get('meta_description', ''),
            featured_media_id=featured_media_id,
        )

        result.update(wp_result)
        job.mark_done(result)

        # Post to Threads — failure must NOT affect WP publish status
        if job.project.threads_enabled:
            try:
                user = job.user
                if user.threads_user_id and user.threads_access_token:
                    text = build_threads_text(job.title, wp_result['wp_post_url'], job.keyword)
                    threads_id = post_to_threads(user.threads_user_id, user.threads_access_token, text)
                    result['threads_post_id'] = threads_id
                    job.result = result
                    job.save(update_fields=['result', 'updated_at'])
            except Exception:
                pass

    except Exception as e:
        job.mark_failed(str(e))

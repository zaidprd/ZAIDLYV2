"""Smoke test setiap halaman dari kursi customer baru.

Jalan via: ./.venv/Scripts/python.exe smoke_test_ux.py
Tujuan: pastikan setiap halaman 200 OK + tangkap masalah cepat (link rusak, dst).
NOT a unit test — script audit yang menulis laporan ke stdout.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
os.environ.setdefault('USE_SQLITE', 'True')
os.environ.setdefault('SECRET_KEY', 'audit-secret')
os.environ.setdefault('AI_PROVIDER', 'mock')
os.environ.setdefault('ALLOWED_HOSTS', 'testserver,localhost,127.0.0.1')
django.setup()

from django.test import Client
from django.urls import reverse

from accounts.models import User
from billing.models import CreditPackage
from projects.models import Project, WordPressSite
from queue_manager.models import QueueJob


def main():
    # Bersihkan & seed minimal data
    User.objects.filter(email='customer@test.com').delete()
    u = User.objects.create_user(username='cust', email='customer@test.com', password='pw12345678')
    u.credits = 5
    u.save()

    if not CreditPackage.objects.exists():
        from django.core.management import call_command
        call_command('seed_packages', verbosity=0)

    p = Project.objects.create(user=u, name='Blog Saya', language='id', tone='informative',
                               writing_style='blog', default_length=1500)
    WordPressSite.objects.create(project=p, name='Demo WP', url='https://demo.example',
                                 username='wp', app_password='xxxx', is_active=True)
    j_gen = QueueJob.objects.create(user=u, project=p, job_type=QueueJob.TYPE_GENERATE,
                                    keyword='cara memulai blog', title='Cara Memulai Blog',
                                    status=QueueJob.PUBLISHED, result={
                                        'article_html': '<h2>Intro</h2><p>...</p>',
                                        'meta_title': 'Cara Memulai Blog', 'slug': 'cara-memulai-blog',
                                        'meta_description': 'Panduan singkat memulai blog.',
                                        'image_url': 'https://placehold.co/1024x576', 'image_alt': 'blog',
                                        'schema_jsonld': '{}', 'seo': {'score': 85, 'passed': True, 'checks': [],
                                                                       'failures': [], 'word_count': 1500,
                                                                       'keyword_density': 1.2, 'h2_count': 5},
                                        'quality_passed': True})
    j_fail = QueueJob.objects.create(user=u, project=p, job_type=QueueJob.TYPE_GENERATE,
                                     keyword='gagal', title='Gagal', status=QueueJob.FAILED,
                                     error_message='Mock failure')

    c = Client()
    c.force_login(u)

    pages = [
        ('Login (logged-out)', 'login', [], False),
        ('Register', 'register', [], False),
        ('Dashboard', 'dashboard', [], True),
        ('Profile', 'profile', [], True),
        ('Project list', 'project_list', [], True),
        ('Project detail', 'project_detail', [p.pk], True),
        ('Project new', 'project_new', [], True),
        ('Project edit', 'project_edit', [p.pk], True),
        ('Project site new', 'site_new', [p.pk], True),
        ('Generate new', 'generate_new', [], True),
        ('Generate result (done)', 'generate_result', [j_gen.pk], True),
        ('Generate result (failed)', 'generate_result', [j_fail.pk], True),
        ('Bulk new', 'bulk_new', [], True),
        ('Queue list', 'queue_list', [], True),
        ('Queue detail', 'queue_detail', [j_gen.pk], True),
        ('Credit history', 'credit_history', [], True),
        ('Package list', 'package_list', [], True),
        ('Campaign list', 'campaign_list', [], True),
    ]

    findings = []
    print(f"{'PAGE':32} {'STATUS':>7}  NOTES")
    print('-' * 100)
    for label, name, args, auth in pages:
        client = c if auth else Client()
        try:
            url = reverse(name, args=args)
            resp = client.get(url, follow=True)
            note = ''
            if resp.status_code != 200:
                note = f"non-200 ({resp.status_code})"
                findings.append((label, note))
            # Cek konten visual
            body = resp.content.decode('utf-8', errors='ignore')
            if 'TemplateSyntaxError' in body or 'NoReverseMatch' in body:
                note = (note + ' · template error').strip(' ·')
                findings.append((label, 'template error'))
            print(f"{label:32} {resp.status_code:>7}  {note}")
        except Exception as e:
            print(f"{label:32} {'ERR':>7}  {e}")
            findings.append((label, str(e)))

    # Coba checkout mock untuk pastikan flow beli kredit utuh
    print()
    pkg = CreditPackage.objects.filter(is_active=True).first()
    if pkg:
        resp = c.post(reverse('package_checkout', args=[pkg.pk]), follow=True)
        ok = resp.status_code == 200 and b'Mock' in resp.content
        print(f"Checkout flow ({pkg.name}): {'OK' if ok else 'BROKEN — ' + str(resp.status_code)}")

    print()
    if findings:
        print(f"\n!!! {len(findings)} masalah ditemukan:")
        for label, note in findings:
            print(f"  - {label}: {note}")
    else:
        print("Semua halaman OK (tidak ada error template / non-200).")


if __name__ == '__main__':
    main()

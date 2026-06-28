from django.db import models
from django.conf import settings


class Project(models.Model):
    LANGUAGE_CHOICES = [('id', 'Bahasa Indonesia'), ('en', 'English')]
    TONE_CHOICES = [
        ('formal', 'Formal'),
        ('professional', 'Profesional'),
        ('casual', 'Santai'),
        ('educational', 'Edukatif'),
        ('persuasive', 'Persuasif'),
        ('informative', 'Informatif'),
    ]
    WRITING_STYLE_CHOICES = [
        ('blog', 'Blog'),
        ('review', 'Review'),
        ('tutorial', 'Tutorial'),
        ('listicle', 'Listicle'),
        ('evergreen', 'Evergreen'),
        ('news', 'News'),
    ]
    LENGTH_CHOICES = [
        (1000, '1000 kata'),
        (1500, '1500 kata'),
        (2000, '2000 kata'),
        (3000, '3000 kata'),
        (5000, '5000+ kata'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=200)
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='id')
    target_audience = models.CharField(max_length=500, blank=True)
    tone = models.CharField(max_length=50, choices=TONE_CHOICES, default='informative')
    writing_style = models.CharField(max_length=20, choices=WRITING_STYLE_CHOICES, default='blog')
    default_length = models.PositiveIntegerField(choices=LENGTH_CHOICES, default=1500)
    brand_voice = models.TextField(blank=True, help_text='Karakter/gaya brand yang harus tercermin di artikel.')
    default_cta = models.CharField(max_length=300, blank=True, help_text='Call-to-action default di akhir artikel.')
    ai_model = models.CharField(max_length=100, default='gpt-4o-mini')
    auto_publish = models.BooleanField(default=False)
    schedule_times = models.CharField(
        max_length=100, blank=True,
        help_text='Jam publish, pisahkan koma. Contoh: 08:00,13:00,20:00'
    )
    daily_limit = models.PositiveIntegerField(default=0, help_text='0 = tidak terbatas')
    threads_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class WordPressSite(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sites')
    name = models.CharField(max_length=200)
    url = models.URLField()
    username = models.CharField(max_length=200)
    app_password = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.url})"

    def save(self, *args, **kwargs):
        self.url = self.url.rstrip('/')
        super().save(*args, **kwargs)

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    credits = models.IntegerField(default=10)
    credits_used = models.IntegerField(default=0)
    plan = models.CharField(max_length=50, default='free')
    threads_user_id = models.CharField(max_length=100, blank=True)
    threads_access_token = models.CharField(max_length=1000, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    @property
    def display_name(self):
        return self.get_full_name() or self.email.split('@')[0]

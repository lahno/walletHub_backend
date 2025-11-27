from django.db import models
from django.contrib.auth.models import AbstractUser
from django_celery_results.models import TaskResult


class User(AbstractUser):
    email = models.EmailField(unique=True)
    settings = models.JSONField(default=dict, blank=True)

from django.db import models

from authenticate.models import User


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    message_type = models.CharField(max_length=20)
    delivered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "delivered", "created_at"]),
        ]


class TelegramSubscriber(models.Model):
    chat_id = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"TelegramSubscriber(chat_id={self.chat_id})"

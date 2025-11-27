from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

UserModel = get_user_model()


class Client(models.Model):
    class ClientType(models.TextChoices):
        MODEL = "model", "Model"
        MANAGER = "manager", "Manager"
        CUSTOM = "custom", "Custom"

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=12, choices=ClientType.choices, default=ClientType.CUSTOM)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Client {self.id} - {self.name}"


class UserClient(models.Model):
    user = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name="user_clients"
    )
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="client_users"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "client")  # Уникальная связь между user и account
        verbose_name = "User Client"
        verbose_name_plural = "User Clients"

    def __str__(self):
        return f"{self.user.username} - {self.client.name}"

    def clean(self):
        # Проверяем уникальность сочетания user и name
        if (
            UserClient.objects.exclude(pk=self.pk)
            .filter(user=self.user, client__name=self.client.name)
            .exists()
        ):
            self.client.delete()
            raise ValidationError("Этот client уже связан с данным пользователем.")

    def save(self, *args, **kwargs):
        self.clean()  # Вызываем проверку перед сохранением
        super().save(*args, **kwargs)

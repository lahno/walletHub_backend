from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from authenticate.models import User
from authenticate.tasks import send_welcome_email_task
import json


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Поля, отображаемые в списке пользователей
    list_display = (
        "id",
        "username",
        "email",
        "settings_preview",
        "is_staff",
        "is_active",
        "date_joined",
        "last_login",
    )
    list_display_links = (
        "username",
        "email",
    )  # Логин и email становится ссылкой на форму редактирования

    # Поля, доступные для поиска
    search_fields = ("username", "email")

    # Фильтры для списка пользователей
    list_filter = ("is_staff", "is_active", "date_joined")

    # Поля, отображаемые как только для чтения
    readonly_fields = ("date_joined", "last_login")

    # Структура разделов на странице редактирования пользователя
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "email")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important Dates", {"fields": ("last_login", "date_joined")}),
        (
            "Custom Fields",
            {"fields": ("settings",)},
        ),  # Здесь добавлено поле `settings`, если оно нужно
    )

    # Поля для добавления нового пользователя
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2"),
            },
        ),
    )
    # Сортировка пользователей
    ordering = ("-date_joined",)
    # Поля для редактирования списка прямо из таблицы
    list_editable = ("is_active",)

    # Действие для отправки всем выбранным пользователям приветственного email
    actions = ["send_welcome_email"]

    def settings_preview(self, obj):
        """
        Отображает содержимое JSON-поля `settings` в удобном виде.
        """
        if not obj.settings:
            return "No Data"
        try:
            # Преобразуем JSON в читаемую строку
            pretty_settings = json.dumps(obj.settings, indent=2)
            return format_html(
                '<pre style="max-height:100px; overflow:auto;">{}</pre>',
                pretty_settings,
            )
        except (TypeError, json.JSONDecodeError):
            return "Invalid JSON"

    settings_preview.short_description = "Settings"  # Название колонки для отображения
    settings_preview.allow_tags = True

    def send_welcome_email(self, request, queryset):
        for user in queryset:
            if user.email:
                send_welcome_email_task.delay(user.email, user.username)
        self.message_user(request, f"Письма поставлены в очередь на отправку")

    send_welcome_email.short_description = "Отправить приветственный email"

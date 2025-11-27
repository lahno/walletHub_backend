from django.contrib import admin
from django.utils.html import format_html
from .models import Notification
import logging

logger = logging.getLogger(__name__)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "get_user",
        "message_preview",
        "message_type",
        "delivered",
        "created_at",
    )
    list_filter = ("delivered", "message_type", "created_at")
    search_fields = ("user__email", "user__username", "message")
    readonly_fields = ("created_at",)
    raw_id_fields = ("user",)
    date_hierarchy = "created_at"
    list_per_page = 50

    actions = [
        "mark_as_delivered",
        "mark_as_undelivered",
        "clear_old_notifications",
        "safe_delete_selected",
    ]

    def safe_delete_selected(self, request, queryset):
        """Безопасное массовое удаление выбранных уведомлений"""
        try:
            count = 0
            errors = []
            for obj in queryset:
                try:
                    obj.delete()
                    count += 1
                except Exception as e:
                    errors.append(f"Ошибка при удалении {obj.id}: {str(e)}")
                    logger.error(f"Ошибка при удалении уведомления {obj.id}: {str(e)}")

            if count > 0:
                self.message_user(request, f"Успешно удалено {count} уведомлений")

            if errors:
                for error in errors:
                    self.message_user(request, error, level="ERROR")

        except Exception as e:
            logger.error(f"Общая ошибка при массовом удалении: {str(e)}")
            self.message_user(
                request,
                f"Произошла ошибка при массовом удалении: {str(e)}",
                level="ERROR",
            )

    safe_delete_selected.short_description = "Удалить выбранные уведомления"

    def message_preview(self, obj):
        """Сокращенный предпросмотр сообщения"""
        if len(obj.message) > 50:
            return obj.message[:50] + "..."
        return obj.message

    message_preview.short_description = "Сообщение"

    def get_user(self, obj):
        """Отображение пользователя со ссылкой"""
        return format_html(
            '<a href="/admin/authenticate/user/{}/change/">{}</a>',
            obj.user.id,
            obj.user.username,
        )

    get_user.short_description = "Пользователь"
    get_user.admin_order_field = "user"

    def has_add_permission(self, request):
        """Запрет на создание уведомлений через админку"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Проверка прав на удаление"""
        return request.user.is_superuser

    def delete_queryset(self, request, queryset):
        """Безопасное массовое удаление"""
        try:
            deleted_count = 0
            for obj in queryset:
                try:
                    obj.delete()
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Ошибка при удалении уведомления {obj.id}: {str(e)}")
                    self.message_user(
                        request,
                        f"Ошибка при удалении уведомления {obj.id}: {str(e)}",
                        level="ERROR",
                    )

            if deleted_count > 0:
                self.message_user(
                    request, f"Успешно удалено {deleted_count} уведомлений"
                )
        except Exception as e:
            logger.error(f"Общая ошибка при массовом удалении: {str(e)}")
            self.message_user(
                request,
                f"Произошла ошибка при массовом удалении: {str(e)}",
                level="ERROR",
            )

    def delete_model(self, request, obj):
        """Безопасное удаление одного объекта"""
        try:
            obj.delete()
            self.message_user(request, f"Уведомление {obj.id} успешно удалено")
        except Exception as e:
            logger.error(f"Ошибка при удалении уведомления {obj.id}: {str(e)}")
            self.message_user(
                request,
                f"Ошибка при удалении уведомления {obj.id}: {str(e)}",
                level="ERROR",
            )

    def mark_as_delivered(self, request, queryset):
        try:
            updated = queryset.update(delivered=True)
            self.message_user(
                request, f"Отмечено как доставленные: {updated} уведомлений"
            )
        except Exception as e:
            logger.error(f"Ошибка при отметке доставленных: {str(e)}")
            self.message_user(
                request, f"Ошибка при отметке доставленных: {str(e)}", level="ERROR"
            )

    mark_as_delivered.short_description = "Отметить как доставленные"

    def mark_as_undelivered(self, request, queryset):
        try:
            updated = queryset.update(delivered=False)
            self.message_user(
                request, f"Отмечено как недоставленные: {updated} уведомлений"
            )
        except Exception as e:
            logger.error(f"Ошибка при отметке недоставленных: {str(e)}")
            self.message_user(
                request, f"Ошибка при отметке недоставленных: {str(e)}", level="ERROR"
            )

    mark_as_undelivered.short_description = "Отметить как недоставленные"

    def clear_old_notifications(self, request, queryset):
        """Очистка старых доставленных уведомлений"""
        from django.utils import timezone
        from datetime import timedelta

        try:
            cutoff_date = timezone.now() - timedelta(days=30)
            count = queryset.filter(
                delivered=True, created_at__lt=cutoff_date
            ).delete()[0]

            self.message_user(request, f"Успешно удалено {count} старых уведомлений")
        except Exception as e:
            logger.error(f"Ошибка при очистке старых уведомлений: {str(e)}")
            self.message_user(
                request,
                f"Ошибка при очистке старых уведомлений: {str(e)}",
                level="ERROR",
            )

    clear_old_notifications.short_description = (
        "Удалить старые доставленные уведомления"
    )

    def get_actions(self, request):
        """Замена стандартного действия удаления на безопасное"""
        actions = super().get_actions(request)
        # Удаляем стандартное действие удаления
        if "delete_selected" in actions:
            del actions["delete_selected"]

        # Ограничиваем доступ к опасным действиям для не-суперпользователей
        if not request.user.is_superuser:
            if "safe_delete_selected" in actions:
                del actions["safe_delete_selected"]
            if "clear_old_notifications" in actions:
                del actions["clear_old_notifications"]

        return actions

    def changelist_view(self, request, extra_context=None):
        """Добавление статистики в список уведомлений"""
        response = super().changelist_view(request, extra_context)

        if hasattr(response, "context_data"):
            qs = response.context_data["cl"].queryset
            response.context_data["total_notifications"] = qs.count()
            response.context_data["undelivered_notifications"] = qs.filter(
                delivered=False
            ).count()

        return response

    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related("user")

    class Media:
        css = {"all": ("admin/css/custom.css",)}

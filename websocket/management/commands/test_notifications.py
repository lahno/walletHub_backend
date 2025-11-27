from django.core.management.base import BaseCommand
from websocket.consumers import send_notification_to_user, send_broadcast_notification


class Command(BaseCommand):
    """
    Примеры использования:
    python manage.py test_notifications --type info --message "Привет!" --user_id 2
    python manage.py test_notifications --type success --message "Всем привет!"
    """

    help = "Отправка тестовых уведомлений"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user_id",
            type=int,
            help="ID пользователя (если не указан - отправка всем)",
            required=False,
        )
        parser.add_argument(
            "--message",
            type=str,
            help="Текст сообщения",
            default="Тестовое уведомление",
        )
        parser.add_argument(
            "--type",
            type=str,
            help="Тип уведомления (info, success, warning, error)",
            default="info",
            choices=["info", "success", "warning", "error"],
        )

    def handle(self, *args, **options):
        message = options["message"]
        user_id = options.get("user_id")
        m_type = options["type"]

        try:
            if user_id:
                # Отправка конкретному пользователю
                send_notification_to_user.delay(
                    user_id=user_id, message=message, m_type=m_type
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Уведомление "{message}" отправлено пользователю {user_id}'
                    )
                )
            else:
                # Broadcast-сообщение всем
                send_broadcast_notification.delay(message=message, m_type=m_type)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Broadcast-уведомление "{message}" отправлено всем пользователям'
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Ошибка при отправке уведомления: {str(e)}")
            )

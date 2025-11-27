import asyncio
from urllib.parse import parse_qs

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
import json

from channels.layers import get_channel_layer

# from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.backends import TokenBackend

from app import settings
from authenticate.models import User
from notification.models import Notification
import logging

logger = logging.getLogger(__name__)


class ProcessConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.group_name = None

    async def connect(self):
        # Получаем имя группы задачи (по её ID)
        self.group_name = f'group_{self.scope["url_route"]["kwargs"]["task_id"]}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Отключить WebSocket из группы
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def task_canceled(self, event):
        # Обрабатываем сообщение о том, что задача была отменена
        await self.send(
            text_data=json.dumps(
                {
                    "status": "canceled",
                    "message": event.get("message", ""),
                    "message_error": event.get("message_error", ""),
                    "progress": event["progress"],
                    "iteration": event["iteration"],
                    "success_iteration": event["success_iteration"],
                    "error_iteration": event["error_iteration"],
                    "data": event.get("data", {}),
                }
            )
        )

    async def process_update(self, event):
        # Отправка данных клиенту
        await self.send(
            text_data=json.dumps(
                {
                    "message": event.get("message", ""),
                    "message_error": event.get("message_error", ""),
                    "progress": event["progress"],
                    "iteration": event["iteration"],
                    "success_iteration": event["success_iteration"],
                    "error_iteration": event["error_iteration"],
                    "data": event.get("data", {}),
                }
            )
        )


class NotificationUserConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.room_name = None
        self.keep_alive_task = None

    async def connect(self):
        self.user = await self.get_user_from_token()
        if self.user is None or isinstance(self.user, AnonymousUser):
            await self.close()
            return

        self.room_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()
        self.keep_alive_task = asyncio.create_task(self.ping_loop())

        # Отправляем непрочитанные уведомления только после установки соединения
        undelivered = await self.get_undelivered_notifications()
        for notification in undelivered:
            await self.send_notification(
                {
                    "message": notification.message,
                    "m_type": notification.message_type,
                    "notification_id": notification.id,
                }
            )

    @database_sync_to_async
    def get_undelivered_notifications(self):
        return list(
            Notification.objects.filter(user=self.user, delivered=False).order_by(
                "created_at"
            )
        )

    async def disconnect(self, close_code):
        if self.user:
            await self.channel_layer.group_discard(self.room_name, self.channel_name)
        if self.keep_alive_task:
            self.keep_alive_task.cancel()

    async def receive(self, text_data=None, bytes_data=None):
        """Обработка входящих сообщений"""
        try:
            content = json.loads(text_data)
            await self.receive_json(content)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def receive_json(self, content):
        """Обработка декодированного JSON"""
        if content.get("type") == "acknowledgement":
            notification_id = content.get("notification_id")
            if notification_id:
                await self.mark_as_delivered(notification_id)

    async def send_notification(self, event):
        notification = {
            "message": event.get("message"),
            "m_type": event.get("m_type", "default_value"),
            "notification_id": event.get("notification_id", None),
        }
        await self.send(text_data=json.dumps(notification))

    @database_sync_to_async
    def get_user_from_token(self):
        query_string = self.scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token = params.get("token", [None])[0]

        if not token:
            return AnonymousUser()

        try:
            token_backend = TokenBackend(
                algorithm="HS256", signing_key=settings.SECRET_KEY
            )
            valid_data = token_backend.decode(token, verify=True)
            user_id = valid_data["user_id"]
            return User.objects.get(id=user_id)
        except Exception as e:
            logger.error(f"Invalid token: {e}")
            return AnonymousUser()

    @database_sync_to_async
    def mark_as_delivered(self, notification_id):
        try:
            Notification.objects.filter(
                id=notification_id,
                user=self.user,  # Важно проверять, что уведомление принадлежит пользователю
            ).update(delivered=True)
            return True
        except Exception as e:
            logger.error(f"Error marking notification as delivered: {e}")
            return False

    async def ping_loop(self):
        try:
            while True:
                await asyncio.sleep(30)  # каждые 30 секунд
                await self.send(text_data=json.dumps({"type": "ping"}))
        except asyncio.CancelledError:
            pass


class BroadcastNotificationConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.broadcast_group = "notifications"  # Общая группа для всех пользователей
        self.keep_alive_task = None

    async def connect(self):
        # Проверяем авторизацию пользователя
        self.user = await self.get_user_from_token()
        if self.user is None or isinstance(self.user, AnonymousUser):
            await self.close()
        else:
            # Добавляем пользователя в общую группу для broadcast-сообщений
            await self.channel_layer.group_add(self.broadcast_group, self.channel_name)
            await self.accept()
            self.keep_alive_task = asyncio.create_task(self.ping_loop())

    async def disconnect(self, close_code):
        if self.user:
            await self.channel_layer.group_discard(
                self.broadcast_group, self.channel_name
            )
        if self.keep_alive_task:
            self.keep_alive_task.cancel()

    async def receive(self, text_data=None, bytes_data=None):
        """Обработка входящих сообщений"""
        try:
            content = json.loads(text_data)
            await self.receive_json(content)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def receive_json(self, content):
        """Обработка декодированного JSON"""
        if content.get("type") == "acknowledgement":
            notification_id = content.get("notification_id")
            if notification_id:
                await self.mark_as_delivered(notification_id)

    async def send_notification(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "message": event["message"],
                    "m_type": event["m_type"],
                    "notification_id": event.get("notification_id"),
                    "is_broadcast": event.get("is_broadcast", False),
                }
            )
        )

    @database_sync_to_async
    def get_user_from_token(self):
        query_string = self.scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token = params.get("token", [None])[0]

        if not token:
            return AnonymousUser()

        try:
            token_backend = TokenBackend(
                algorithm="HS256", signing_key=settings.SECRET_KEY
            )
            valid_data = token_backend.decode(token, verify=True)
            user_id = valid_data["user_id"]
            # User = get_user_model()
            return User.objects.get(id=user_id)
        except Exception as e:
            logger.error(f"Invalid token: {e}")
            return AnonymousUser()

    @database_sync_to_async
    def mark_as_delivered(self, notification_id):
        try:
            Notification.objects.filter(
                id=notification_id,
                user=self.user,  # Важно проверять, что уведомление принадлежит пользователю
            ).update(delivered=True)
            return True
        except Exception as e:
            logger.error(f"Error marking notification as delivered: {e}")
            return False

    async def ping_loop(self):
        try:
            while True:
                await asyncio.sleep(30)  # каждые 30 секунд
                await self.send(text_data=json.dumps({"type": "ping"}))
        except asyncio.CancelledError:
            pass


@shared_task
def send_notification_to_user(user_id, message, m_type="info"):
    # Сначала сохраняем в базу
    notification = Notification.objects.create(
        user_id=user_id, message=message, message_type=m_type
    )

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "send_notification",
            "message": message,
            "m_type": m_type,
            "notification_id": notification.id,
        },
    )


@shared_task
def send_broadcast_notification(message, m_type="info"):
    # User = get_user_model()
    channel_layer = get_channel_layer()

    for user in User.objects.filter(is_active=True):
        # Создаем уведомление для каждого пользователя
        notification = Notification.objects.create(
            user=user, message=message, message_type=m_type
        )

        # Отправляем персональное уведомление каждому пользователю
        async_to_sync(channel_layer.group_send)(
            f"user_{user.id}",  # Отправляем в личную группу пользователя
            {
                "type": "send_notification",
                "message": message,
                "m_type": m_type,
                "notification_id": notification.id,
                "is_broadcast": True,
            },
        )

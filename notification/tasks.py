import asyncio
import logging
from datetime import timedelta
from typing import Iterable

from aiogram.client.default import DefaultBotProperties
from django.utils.timezone import now
from celery import shared_task

from app import settings
from notification.models import Notification, TelegramSubscriber
from websocket.consumers import send_broadcast_notification

from aiogram import Bot
from aiogram.enums import ParseMode

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_notifications():
    # Удаляем доставленные уведомления старше 30 дней
    cleanup_date = now() - timedelta(days=30)
    deleted_count, _ = Notification.objects.filter(
        delivered=True, created_at__lt=cleanup_date
    ).delete()

    # Отправка уведомления через WebSocket
    if deleted_count:
        send_broadcast_notification.delay(message=f"{deleted_count} старых уведомлений удалено.")

    return f"{deleted_count} old notifications deleted."


async def _broadcast_telegram_notification_async(
    message: str, chat_ids: Iterable[int]
) -> None:
    """
    Асинхронная часть отправки сообщений через aiogram Bot.
    Получает уже подготовленный список chat_id, поэтому не трогает ORM.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not configured")
        return

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    try:
        for chat_id in chat_ids:
            try:
                await bot.send_message(chat_id=chat_id, text=message)
            except Exception:
                logger.exception(
                    "Error sending telegram message to chat_id=%s", chat_id
                )
                continue
    finally:
        try:
            await bot.session.close()
        except Exception:
            logger.exception("Error while closing Telegram bot session")


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def broadcast_telegram_notification(self, message: str) -> None:
    """
    Синхронная Celery-таска, которая:
      1) синхронно получает список chat_id через ORM;
      2) запускает асинхронную отправку сообщений в Telegram.
    """
    # ВАЖНО: ORM вызываем ТОЛЬКО здесь, в синхронном контексте
    chat_ids = list(
        TelegramSubscriber.objects.filter(is_active=True).values_list(
            "chat_id", flat=True
        )
    )

    if not chat_ids:
        logger.info("No active Telegram subscribers found")
        return

    try:
        asyncio.run(_broadcast_telegram_notification_async(message, chat_ids))
    except Exception:
        logger.exception("Unexpected error in broadcast_telegram_notification")
        # При желании можно включить повтор:
        # raise self.retry(exc=exc)
        return

import asyncio
import logging
import os

import django
from aiogram.client.default import DefaultBotProperties
from asgiref.sync import sync_to_async

from app import settings

# Указываем настройки Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

django.setup()

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command

from notification.models import TelegramSubscriber  # замените your_app на приложение где модель


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    chat_id = str(message.chat.id)
    sub, created = await sync_to_async(TelegramSubscriber.objects.get_or_create)(
        chat_id=chat_id,
        defaults={"is_active": True},
    )

    if not created and not sub.is_active:
        sub.is_active = True
        await sync_to_async(sub.save)(update_fields=["is_active"])

    text = (
        "Вы подписаны на уведомления ✅\n\n"
        "Вы будете получать все события из системы.\n"
        "Для остановки уведомлений используйте команду /stop."
    )
    await message.answer(text)
    logger.info("Telegram subscriber %s subscribed", chat_id)


@dp.message(Command("stop"))
async def cmd_stop(message: Message) -> None:
    chat_id = str(message.chat.id)

    try:
        # Получаем подписчика в отдельном потоке
        sub = await sync_to_async(TelegramSubscriber.objects.get)(chat_id=chat_id)

        if sub.is_active:
            sub.is_active = True and False or False  # will be fixed below
            await sync_to_async(sub.save)(update_fields=["is_active"])
            await message.answer("Вы отписаны от уведомлений ❌")
        else:
            await message.answer("Вы уже были отписаны.")
    except TelegramSubscriber.DoesNotExist:
        await message.answer("Вы не были подписаны.")

    logger.info("Telegram subscriber %s unsubscribed", chat_id)


@dp.message(F.text)
async def any_text(message: Message) -> None:
    """
    Простейший help на все остальные сообщения.
    """
    await message.answer(
        "Команды бота:\n"
        "/start — подписаться на уведомления\n"
        "/stop — отписаться от уведомлений"
    )


async def main() -> None:
    logger.info("Starting aiogram bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
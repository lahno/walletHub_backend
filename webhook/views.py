from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
import logging

from client.models import UserClient
from wallet.models import Wallet
from websocket.consumers import send_notification_to_user
from notification.tasks import broadcast_telegram_notification

logger = logging.getLogger("django")


class TatumWebhookView(APIView):
    """
    Обработчик вебхуков от Tatum.
    """
    authentication_classes: list = []  # вебхуки не требуют аутентификации
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        payload = request.data

        # Логируем сырое тело на всякий случай
        logger.info("Received Tatum webhook: %s", payload)

        # 1. Достаём нужные поля
        subscription_id = payload.get("subscriptionId")
        address = payload.get("address")

        if not subscription_id or not address:
            logger.warning(
                "Webhook without subscriptionId or address: %s",
                payload,
            )
            # всё равно отвечаем 200/OK, чтобы Tatum не спамил ретраями
            return Response("OK", status=status.HTTP_200_OK)

        # 2. Ищем Wallet
        try:
            wallet = Wallet.objects.select_related("client").get(
                subscription_id=subscription_id,
                address=address,
            )
        except Wallet.DoesNotExist:
            logger.warning(
                "Wallet not found for subscription %s and address %s",
                subscription_id,
                address,
            )
            # тоже 200/OK, иначе Tatum будет пытаться снова
            return Response("OK", status=status.HTTP_200_OK)

        # 3. Отправляем уведомление пользователю
        self._notify_wallet_owner(wallet, payload)

        # 4. Возвращаем положительный ответ
        return Response("OK", status=status.HTTP_200_OK)

    @staticmethod
    def _notify_wallet_owner(wallet: Wallet, payload: dict) -> None:
        """
        Отправка уведомления пользователю, создавшему кошелёк.
        """
        client = wallet.client

        # Пытаемся найти пользователя, связанного с этим клиентом
        user_client = (
            UserClient.objects
            .select_related("user")
            .filter(client=client)
            .order_by("created_at")
            .first()
        )

        if user_client is None or user_client.user is None:
            logger.warning(
                "Cannot notify wallet owner: no UserClient entry for client %s (wallet=%s)",
                client.id,
                wallet.id,
            )
            return

        user = user_client.user
        amount = payload.get("amount")
        asset = payload.get("asset")
        tx_id = payload.get("txId")
        tx_type = payload.get("type")

        logger.info(
            "Notify user about tx: user=%s wallet=%s amount=%s asset=%s tx=%s type=%s",
            getattr(user, "id", None),
            wallet.id,
            amount,
            asset,
            tx_id,
            tx_type,
        )

        send_notification_to_user.delay(
            user.id,
            f"Новая транзакция у клиента {client.name} - {tx_id}",
        )

        text = (
            f"<b>Новая транзакция!</b>\n"
            f"Клиент: <b>{client.name}</b>\n"
            f"Сумма: <code>{amount}</code>\n"
            f"TX ID: <code>{tx_id}</code>"
        )

        # Запускаем асинхронную Celery-задачу отправки уведомлений в телеграмм
        broadcast_telegram_notification.delay(text)

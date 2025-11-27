from django.core.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status, permissions
from rest_framework.views import APIView

from app import settings
from client.models import Client, UserClient
from app.external.tatum_api import WalletApiClient, WalletApiError
from wallet.models import Wallet
from wallet.serializers import WalletSerializer


class WalletView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    CHAIN_BY_WALLET_TYPE = {
        "tron": "TRON",
        "bitcoin": "BTC",
        "ethereum": "ETH",
    }

    @staticmethod
    def get_queryset(user):
        client_ids = UserClient.objects.filter(user=user).values_list(
            "client_id", flat=True
        )
        return Wallet.objects.filter(client_id__in=client_ids)

    def post(self, request):
        """
        Создать новый Wallet для клиента, принадлежащего текущему пользователю.
        Ожидает:
        - client: ID клиента
        - type: тип кошелька (ethereum / tron / bitcoin)
        """
        user = request.user
        client_id = request.data.get("client")
        wallet_type = request.data.get("type")

        if not client_id or not wallet_type:
            raise ValidationError(
                {"detail": "Поля 'client' и 'type' являются обязательными."}
            )

        # Проверяем валидность типа кошелька
        if wallet_type not in Wallet.WalletType.values:
            raise ValidationError(
                {"type": f"Неверный тип кошелька. Допустимые: {list(Wallet.WalletType.values)}"}
            )

        # 1. Проверяем, что указанный client принадлежит текущему пользователю
        is_bound = UserClient.objects.filter(user=user, client_id=client_id).exists()
        if not is_bound:
            # либо клиент не существует, либо он не привязан к пользователю
            raise PermissionDenied("У вас нет доступа к этому клиенту.")

        try:
            client = Client.objects.get(pk=client_id)
        except Client.DoesNotExist:
            # маловероятный кейс (мы проверили через UserClient), но на всякий случай
            raise ValidationError({"client": "Указанный client не найден."})

        # 2. Работа с внешним API
        api = WalletApiClient(
            base_url=settings.TATUM_BASE_URL,
            api_key=settings.TATUM_API_KEY,
        )

        try:
            # 2.1. Генерация mnemonic и xpub
            mnemonic_xpub = api.generate_mnemonic_and_xpub(wallet_type)
            mnemonic = mnemonic_xpub["mnemonic"]
            xpub = mnemonic_xpub["xpub"]

            # Можно сделать index конфигурируемым, пока жёстко 0
            index = 0

            # 2.2. Генерация приватного ключа
            private_key = api.generate_private_key(
                wallet_type=wallet_type,
                mnemonic=mnemonic,
                index=index,
            )

            # 2.3. Генерация адреса
            address = api.generate_address(
                wallet_type=wallet_type,
                xpub=xpub,
                index=index,
            )

            # 2.4 Создаём подписку на транзакции
            chain = self.CHAIN_BY_WALLET_TYPE.get(wallet_type)
            subscription = api.create_subscription(chain, settings.TATUM_WEBHOOK_URL, address)

        except WalletApiError as e:
            raise ValidationError({"detail": f"Ошибка при создании кошелька во внешнем сервисе: {e}"})
        finally:
            api.close()

        # 3. Сохраняем кошелёк в БД
        wallet = Wallet.objects.create(
            client=client,
            type=wallet_type,
            xpub=xpub,
            mnemonic=mnemonic,
            key=private_key,
            address=address,
        )

        # сохраняем subscription_id в модель Wallet:
        if subscription and "id" in subscription:
            wallet.subscription_id = subscription["id"]
            wallet.save(update_fields=["subscription_id"])

        # 4. Возвращаем данные через ваш сериализатор
        serializer = WalletSerializer(wallet)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
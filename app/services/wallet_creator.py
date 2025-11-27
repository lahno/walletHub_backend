from django.db import transaction
import logging

from wallet.models import Wallet
from app.external.tatum_api import WalletApiClient, WalletTypeLiteral, WalletApiError

logger = logging.getLogger(__name__)


DEFAULT_ADDRESS_INDEX = 1


class WalletCreationError(Exception):
    ...


class WalletCreator:
    def __init__(self, api_client: WalletApiClient, webhook_url: str) -> None:
        self.api_client = api_client
        self.webhook_url = webhook_url

    @staticmethod
    def _map_wallet_type_to_chain(wallet_type: WalletTypeLiteral) -> str:
        """
        Преобразование внутреннего типа кошелька в chain для Tatum subscription.
        """
        mapping = {
            "tron": "TRON",
            "bitcoin": "BTC",
            "ethereum": "ETH",
        }
        try:
            return mapping[wallet_type]
        except KeyError:
            raise WalletCreationError(f"Unsupported wallet type for subscription: {wallet_type}")

    @transaction.atomic
    def create_full_wallet(
        self,
        *,
        client,
        wallet_type: WalletTypeLiteral,
        index: int = DEFAULT_ADDRESS_INDEX,
    ) -> Wallet:
        """
        Создаёт кошелёк во внешнем API и пошагово сохраняет данные в модель Wallet.
        """
        # 0. создаём запись кошелька (пока пустые поля)
        wallet = Wallet.objects.create(
            client=client,
            type=wallet_type,
        )

        try:
            # 1) mnemonic + xpub
            step1 = self.api_client.generate_mnemonic_and_xpub(wallet_type)
            wallet.mnemonic = step1["mnemonic"]
            wallet.xpub = step1["xpub"]
            wallet.save(update_fields=["mnemonic", "xpub"])

            # 2) private key
            key = self.api_client.generate_private_key(
                wallet_type=wallet_type,
                mnemonic=wallet.mnemonic,
                index=index,
            )
            wallet.key = key
            wallet.save(update_fields=["key"])

            # 3) address
            address = self.api_client.generate_address(
                wallet_type=wallet_type,
                xpub=wallet.xpub,
                index=index,
            )
            wallet.address = address
            wallet.save(update_fields=["address"])

            # 5) создаём подписку на события по адресу
            chain = self._map_wallet_type_to_chain(wallet_type)
            try:
                subscription_response = self.api_client.create_subscription(
                    chain=chain,
                    url_callback=self.webhook_url,
                    address=address,
                )
            except Exception as exc:
                logger.error("Failed to create Tatum subscription: %s", exc)
                subscription_response = None

            # сохраняем subscription_id в модель Wallet:
            if subscription_response and "id" in subscription_response:
                wallet.subscription_id = subscription_response["id"]
                wallet.save(update_fields=["subscription_id"])

        except (WalletApiError, KeyError) as exc:
            # при ошибке можно пометить кошелёк как неактивный
            wallet.status = False
            wallet.save(update_fields=["status"])
            raise WalletCreationError(f"Не удалось создать кошелёк: {exc}") from exc

        return wallet
import time

from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException
from app import settings
from app.external.tatum_api import WalletApiClient


class BinanceConverter:
    def __init__(self, api_key=None, api_secret=None):
        self.api_key = api_key or settings.BINANCE_API_KEY
        self.api_secret = api_secret or settings.BINANCE_API_SECRET
        if not self.api_key or not self.api_secret:
            raise ValueError("Binance API key and secret are required.")
        self.client = BinanceClient(self.api_key, self.api_secret)

        # Маппинг сетей к торговым парам и символам
        self.network_to_symbol = {
            'bitcoin': 'BTCUSDT',
            'ethereum': 'ETHUSDT',
            'tron': 'TRXUSDT'
        }

    def get_balance(self, asset):
        """Получает баланс актива на Binance (для проверки после перевода)."""
        try:
            balance = self.client.get_asset_balance(asset=asset.upper())
            return float(balance['free'])
        except BinanceAPIException as e:
            raise ValueError(f"Error getting balance for {asset}: {e}")

    def convert_to_usdt(self, network, quantity):
        """
        Конвертирует указанное количество криптовалюты в USDT через market sell order.
        :param network: 'bitcoin', 'ethereum' или 'tron'
        :param quantity: Количество для конвертации (float)
        :return: Детали ордера или ошибка
        """
        symbol = self.network_to_symbol.get(network.lower())
        if not symbol:
            raise ValueError(f"Unsupported network: {network}")

        # Проверяем доступный баланс на Binance
        asset = symbol[:-4]  # BTC, ETH, TRX
        available = self.get_balance(asset)
        if available < quantity:
            raise ValueError(f"Insufficient balance for {asset}: {available} < {quantity}")

        try:
            # Размещаем market sell order
            order = self.client.order_market_sell(
                symbol=symbol,
                quantity=quantity
            )
            return order
        except BinanceAPIException as e:
            raise ValueError(f"Error converting {network} to USDT: {e}")

    def check_and_convert(self, network, tatum_balance, from_private_key, threshold=100.0):
        """
        Проверяет баланс из Tatum и инициирует конвертацию, если >= threshold.
        Предполагает, что средства уже переведены на Binance (добавьте перевод отдельно).
        :param network: Сеть
        :param tatum_balance: Баланс из Tatum (float)
        :param from_private_key: Private key с которого отправляем
        :param threshold: Порог (default 100)
        """
        if tatum_balance < threshold:
            return {"status": "skipped", "reason": f"Balance {tatum_balance} < {threshold}"}

        symbol = self.network_to_symbol.get(network.lower())
        if not symbol:
            raise ValueError(f"Unsupported network (check_and_convert): {network}")

        # Проверяем доступный баланс на Binance
        asset = symbol[:-4]  # BTC, ETH, TRX

        # Здесь добавьте логику перевода с Tatum на Binance deposit address
        deposit_address = self.client.get_deposit_address(coin=asset.upper())

        wallet_api = WalletApiClient(
            base_url=settings.TATUM_BASE_URL,
            api_key=settings.TATUM_API_KEY,
        )

        tx_id = wallet_api.send_transaction(
            wallet_type=network,
            from_private_key=from_private_key,
            to_address=deposit_address,
            amount=tatum_balance
        )

        if tx_id:
            # Как узнать что перевод завершен?
            time.sleep(20)
            return self.convert_to_usdt(network, tatum_balance)

        return {"status": "skipped", "reason": f"Transaction not completed!"}

# Пример использования (в вашем view или webhook):
# converter = BinanceConverter()
# result = converter.check_and_convert('bitcoin', current_balance_from_tatum)
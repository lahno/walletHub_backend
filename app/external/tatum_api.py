from typing import Any, Dict, Literal

import httpx

WalletTypeLiteral = Literal["bitcoin", "ethereum", "tron"]


class WalletApiError(Exception):
    ...


class WalletApiClient:
    def __init__(self, base_url: str, api_key: str, timeout: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client = httpx.Client(timeout=self.timeout)

    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

    def _handle_response(self, resp: httpx.Response) -> Dict[str, Any]:
        if 200 <= resp.status_code < 300:
            return resp.json()
        raise WalletApiError(f"Status {resp.status_code}: {resp.text}")

    # 1) mnemonic + xpub
    def generate_mnemonic_and_xpub(
        self,
        wallet_type: WalletTypeLiteral,
    ) -> Dict[str, str]:
        url = f"{self.base_url}/{wallet_type}/wallet"
        resp = self._client.get(url, headers=self._headers())
        data = self._handle_response(resp)
        return {
            "mnemonic": data["mnemonic"],
            "xpub": data["xpub"],
        }

    # 2) приватный ключ
    def generate_private_key(
        self,
        wallet_type: WalletTypeLiteral,
        mnemonic: str,
        index: int,
    ) -> str:
        url = f"{self.base_url}/{wallet_type}/wallet/priv"
        payload = {
            "mnemonic": mnemonic,
            "index": index,
        }
        resp = self._client.post(url, json=payload, headers=self._headers())
        data = self._handle_response(resp)
        return data["key"]

    # 3) адрес
    def generate_address(
        self,
        wallet_type: WalletTypeLiteral,
        xpub: str,
        index: int,
    ) -> str:
        url = f"{self.base_url}/{wallet_type}/address/{xpub}/{index}"
        resp = self._client.get(url, headers=self._headers())
        data = self._handle_response(resp)
        return data["address"]

    # 4) подписка на события адреса
    def create_subscription(
        self,
        chain: str,
        url_callback: str,
        address: str,
    ) -> Dict[str, Any]:
        """
        Создаёт подписку вида ADDRESS_TRANSACTION (ADDRESS_EVENT) для указанного адреса.
        chain: 'TRON', 'BTC', 'ETH' и т.п. (как ожидает Tatum)
        """
        url = f"{self.base_url}/subscription"
        payload: Dict[str, Any] = {
            "type": "ADDRESS_EVENT",
            "attr": {
                "chain": chain,
                "url": url_callback,
                "address": address,
            },
        }
        resp = self._client.post(url, json=payload, headers=self._headers())
        return self._handle_response(resp)

    def send_transaction(
        self,
        wallet_type: WalletTypeLiteral,
        from_private_key: str,
        to_address: str,
        amount: str,  # Сумма в строковом формате (например, "0.1" для BTC или в wei для ETH)
        fee: str = None,  # Опционально для BTC/Tron
        gas_limit: str = None,  # Опционально для ETH/Tron
        gas_price: str = None,  # Опционально для ETH
    ) -> str:
        """
        Отправляет транзакцию на указанный адрес (например, депозитный счёт Binance для конвертации).
        Возвращает ID транзакции.
        """
        if wallet_type == "bitcoin":
            url = f"{self.base_url}/bitcoin/transaction"
            payload = {
                "fromAddress": [
                    {
                        "privateKey": from_private_key,
                    }
                ],
                "to": [
                    {
                        "address": to_address,
                        "value": float(amount),
                    }
                ],
            }
            if fee:
                payload["fee"] = fee
        elif wallet_type == "ethereum":
            url = f"{self.base_url}/ethereum/transaction"
            payload = {
                "fromPrivateKey": from_private_key,
                "to": to_address,
                "value": amount,  # Ожидается в wei
            }
            if gas_limit:
                payload["gasLimit"] = gas_limit
            if gas_price:
                payload["gasPrice"] = gas_price
        elif wallet_type == "tron":
            url = f"{self.base_url}/tron/transaction"
            payload = {
                "fromPrivateKey": from_private_key,
                "to": to_address,
                "amount": amount,  # В sun для TRX
            }
            if fee:
                payload["feeLimit"] = fee
            if gas_limit:
                payload["gasLimit"] = gas_limit  # Адаптировать под Tron, если нужно
        else:
            raise ValueError(f"Unsupported wallet type: {wallet_type}")

        resp = self._client.post(url, json=payload, headers=self._headers())
        data = self._handle_response(resp)
        return data.get("txId", data.get("hash"))  # Возвращает txId или hash в зависимости от сети

    def close(self) -> None:
        self._client.close()
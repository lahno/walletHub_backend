from django.db import models

from client.models import Client


class Wallet(models.Model):
    class WalletType(models.TextChoices):
        ETH = "ethereum", "Ethereum"
        TRON = "tron", "Tron"
        BTC = "bitcoin", "Bitcoin"

    id = models.BigAutoField(primary_key=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="wallets")
    type = models.CharField(max_length=12, choices=WalletType.choices)
    xpub = models.TextField(null=True, editable=False)
    mnemonic = models.TextField(null=True, editable=False)
    key = models.TextField(null=True, editable=False)
    address = models.TextField(null=True, editable=False)
    status = models.BooleanField(default=True)
    subscription_id = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

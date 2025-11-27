from rest_framework import serializers
from wallet.models import Wallet


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        # mnemonic / key обычно не отдают наружу, поэтому не включаю их в поля ответа
        read_only_fields = ("id", "xpub", "mnemonic", "key", "address", "created_at", "updated_at")
        fields = ("id", "client", "type", "address", "status", "created_at", "updated_at")
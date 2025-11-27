from rest_framework import serializers
from client.models import Client
from wallet.serializers import WalletSerializer


class ClientSerializer(serializers.ModelSerializer):
    wallets = WalletSerializer(many=True, read_only=True)

    class Meta:
        model = Client
        fields = [
            "id",
            "name",
            "type",
            "status",
            "wallets",
            "created_at",
            "updated_at",
        ]

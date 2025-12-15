from rest_framework import serializers
from client.models import Client
from wallet.serializers import WalletSerializer


class ClientSerializer(serializers.ModelSerializer):
    wallets = serializers.SerializerMethodField()

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

    def get_wallets(self, obj):
        qs = obj.wallets.filter(status=True)
        return WalletSerializer(qs, many=True).data
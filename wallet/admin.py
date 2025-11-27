from django.contrib import admin
from .models import Wallet

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    readonly_fields = ("address", "type")  # отобразит поле как read-only
    list_display = ("id", "client", "type", "address", "status")
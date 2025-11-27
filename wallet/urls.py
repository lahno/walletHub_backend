from django.urls import path
from wallet.views import WalletView

urlpatterns = [
    path("", WalletView.as_view(), name="wallet-list"),  # Для списка и создания
    path("<int:pk>/", WalletView.as_view(), name="wallet-detail"),
]

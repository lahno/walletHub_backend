from django.urls import path

from webhook.views import TatumWebhookView

urlpatterns = [
    path("tatum/", TatumWebhookView.as_view(), name="tatum-webhook"),
]


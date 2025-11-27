from django.urls import path, re_path
from .consumers import (
    ProcessConsumer,
    NotificationUserConsumer,
    BroadcastNotificationConsumer,
)

websocket_urlpatterns = [
    path("ws/process_status/<str:task_id>/", ProcessConsumer.as_asgi()),
    re_path(r"ws/notifications/user/$", NotificationUserConsumer.as_asgi()),
    re_path(r"ws/notifications/broadcast/$", BroadcastNotificationConsumer.as_asgi()),
]

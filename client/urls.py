from django.urls import path
from client.views import ClientView

urlpatterns = [
    path("", ClientView.as_view(), name="client-list"),  # Для списка и создания
    path("<int:pk>/", ClientView.as_view(), name="client-detail"),
]

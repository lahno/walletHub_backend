from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status, permissions
from rest_framework.views import APIView

from client.models import UserClient, Client
from client.serializers import ClientSerializer


class ClientView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get_queryset(user):
        """
        Возвращает QuerySet аккаунтов, связанных с текущим пользователем.
        """
        client_ids = UserClient.objects.filter(user=user).values_list(
            "client_id", flat=True
        )
        return Client.objects.filter(id__in=client_ids)

    def get(self, request, pk=None):
        """
        Обрабатывает GET-запросы:
        - Получение списка всех объектов Client, принадлежащих текущему пользователю (если pk не указан).
        - Получение одного объекта Client по ID, принадлежащего текущему пользователю (если pk указан).
        """

        if pk:
            try:
                client = self.get_queryset(request.user).get(pk=pk)
            except Client.DoesNotExist:
                raise NotFound("Client not found")
            serializer = ClientSerializer(client)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            clients = self.get_queryset(request.user)
            serializer = ClientSerializer(clients, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Создать новый Client и привязать его к текущему пользователю."""
        serializer = ClientSerializer(data=request.data)
        if serializer.is_valid():
            client = serializer.save()  # создаём сам Client
            # создаём связь с пользователем
            UserClient.objects.create(user=request.user, client=client)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def put(self, request, pk):
        """Обновить существующий объект Client, принадлежащий текущему пользователю."""
        user = request.user
        try:
            target = self.get_queryset(user).get(pk=pk)
        except Client.DoesNotExist:
            raise NotFound("Target not found")
        serializer = ClientSerializer(target, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Удалить объект Client, принадлежащий текущему пользователю."""
        user = request.user
        try:
            target = self.get_queryset(user).get(pk=pk)
        except Client.DoesNotExist:
            raise NotFound("Target not found")
        target.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
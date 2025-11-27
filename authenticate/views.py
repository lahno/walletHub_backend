from rest_framework import views, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from authenticate.serializers import RegisterSerializer, UserSerializer


class RegisterView(views.APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(views.APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class UserView(views.APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [
        permissions.IsAuthenticated
    ]  # Требуем аутентификацию для всех методов

    def get(self, request):
        """Получение данных о текущем пользователе"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        """Обновление данных пользователя"""
        serializer = UserSerializer(
            request.user, data=request.data, partial=True
        )  # Поддержка частичного обновления

        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """Удаление пользователя"""
        user = request.user
        user.delete()
        return Response(
            {"message": "Пользователь удален"}, status=status.HTTP_204_NO_CONTENT
        )

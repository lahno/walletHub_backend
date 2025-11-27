import logging

from celery import Task
from celery.result import AsyncResult
from django.http import JsonResponse
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from target.tasks import run_recommend_task, run_friend_task
from sender.tasks import run_comment_task

from authenticate.serializers import UserSerializer

logger = logging.getLogger(__name__)


class BaseTaskView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]


class StartFindRecommendTargetsTask(BaseTaskView):
    def get(self, request):
        # Запускаем фоновую задачу
        serializer = UserSerializer(request.user)
        user_data = serializer.data
        user_id = user_data.get("id")

        task = run_recommend_task.apply_async(kwargs={"user_id": user_id})

        # Получаем ID задачи, сгенерированное Celery
        task_id = task.id
        return JsonResponse(
            {
                "message": f'Task {task_id[:5]} started for {user_data.get("username")}',
                "user_id": user_id,
                "task_id": task_id,  # Celery ID используется как task_id
            }
        )


class StartFindFriendsTargetsTask(BaseTaskView):
    def get(self, request):
        # Запускаем фоновую задачу
        serializer = UserSerializer(request.user)
        user_data = serializer.data
        user_id = user_data.get("id")

        task = run_friend_task.apply_async(kwargs={"user_id": user_id})

        # Получаем ID задачи, сгенерированное Celery
        task_id = task.id
        return JsonResponse(
            {
                "message": f'Task {task_id[:5]} started for {user_data.get("username")}',
                "user_id": user_id,
                "task_id": task_id,  # Celery ID используется как task_id
            }
        )


class StartSendCommentsTask(BaseTaskView):
    def get(self, request):
        # Запускаем фоновую задачу
        serializer = UserSerializer(request.user)
        user_data = serializer.data
        user_id = user_data.get("id")

        task = run_comment_task.apply_async(kwargs={"user_id": user_id})

        # Получаем ID задачи, сгенерированное Celery
        task_id = task.id
        return JsonResponse(
            {
                "message": f'Task {task_id[:5]} started for {user_data.get("username")}',
                "user_id": user_id,
                "task_id": task_id,  # Celery ID используется как task_id
            }
        )


def task_status(request, task_id):
    """
    Проверяет статус задачи в Celery по ее `task_id`.
    Возвращает JSON с текущим состоянием и результатом (если доступно).
    """
    try:
        # Создаем AsyncResult для задачи
        result = AsyncResult(task_id)

        # print(f"Task {task_id} status: {result.state}")

        if result.state == "PENDING":
            # Проверяем метаданные задачи для подтверждения ее статуса
            task_meta = result.backend.get_task_meta(task_id)

            if not task_meta or task_meta.get("task_name") is None:
                # Задача не существует, возвращаем соответствующее состояние
                response = {
                    "status": "NOT_FOUND",
                    "result": None,
                    "error": "Task ID not found in backend.",
                }
            else:
                # Задача существует, но находится в статусе ожидания
                response = {
                    "status": "PENDING",  # Просто ожидает выполнения
                    "result": None,
                    "error": None,
                }
        else:
            # Задача находится в других состояниях (например, STARTED, SUCCESS, FAILURE)
            response = {
                "status": result.state,
                "result": result.result if result.state == "SUCCESS" else None,
                "error": str(result.result) if result.state == "FAILURE" else None,
            }

        return JsonResponse(response)  # Возвращаем JSON

    except Exception as e:
        # Обрабатываем ошибки, например если task_id некорректен
        return JsonResponse({"error": str(e)}, status=500)


def stop_task(request, task_id):
    try:
        Task.app.control.revoke(task_id, terminate=True)
        logger.warning(f"Task {task_id} stopped from user successfully")
        return JsonResponse(
            {"status": True, "message": "Task stopped successfully", "task_id": task_id}
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

from django.urls import path

from websocket.views import task_status, stop_task
from websocket.views import (
    StartFindRecommendTargetsTask,
    StartSendCommentsTask,
    StartFindFriendsTargetsTask,
)

urlpatterns = [
    path("task-status/<str:task_id>/", task_status, name="task_status"),
    path("stop-task/<str:task_id>/", stop_task, name="stop_task"),
    path(
        "task/target/find_recommend/",
        StartFindRecommendTargetsTask.as_view(),
        name="start_recommend_task",
    ),
    path(
        "task/target/find_friend/",
        StartFindFriendsTargetsTask.as_view(),
        name="start_friends_task",
    ),
    path(
        "task/sender/send_comment/",
        StartSendCommentsTask.as_view(),
        name="start_comment_task",
    ),
]

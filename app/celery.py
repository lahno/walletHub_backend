from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.signals import task_postrun

# Устанавливаем стандартный модуль настроек Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

app = Celery("app")

# Загрузка конфигурации из settings.py (с префиксом CELERY_)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автоматическое определение задач в приложениях
app.autodiscover_tasks()

# Добавляем параметр для устранения предупреждения
app.conf.broker_connection_retry_on_startup = True

# Настройка отмены долгих задач при потере соединения с брокером
app.conf.worker_cancel_long_running_tasks_on_connection_loss = True

# Ограничение задач на одного воркера для предотвращения утечек памяти и зависаний
app.conf.max_tasks_per_child = 8


def get_active_tasks():
    # Инициализируем инспектор_
    inspector = app.control.inspect()

    # Список запланированных задач
    # scheduled_tasks = inspector.scheduled()

    # Список зарезервированных задач (ожидают выполнения)
    # reserved_tasks = inspector.reserved()

    # Получаем все активные задачи
    return inspector.active()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


@task_postrun.connect
def close_db_connection(**kwargs):
    from django.db import connections

    for conn in connections.all():
        conn.close()

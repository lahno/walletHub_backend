import threading
from typing import Optional

from celery.result import AsyncResult
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import concurrent.futures
import logging
from celery import Task
from django.db import close_old_connections, transaction

from account.models import Account, NotificationType, AccountNotification
from archive.models import Archive
from authenticate.models import User
from ofauth.services.getters import get_invalid_target_skipped_types
from ofauth.validators.response import (
    OFAuthAPIClientResponse,
    InternalVerificationResponse,
)
from target.models import InvalidTarget
from websocket.consumers import send_notification_to_user


class BaseTaskRunner(Task):
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.user_id = kwargs.get("user_id")
        self.channel_layer = get_channel_layer()
        self.group_name = None
        self.task_id = None
        self.user = None
        self.count_success = 0
        self.count_failed = 0
        self.progress = 0
        self.total_iterations = 0
        self.dynamic_total_steps = 0
        self.result = {}
        self.is_stopped = False
        self.cancel_flag = threading.Event()  # Флаг отмены
        self.task_data = []
        super().__init__()

    def run_task(self, *args, **kwargs):
        """
        Запуск задачи Celery с параллельной обработкой логики.
        """
        # Закрытие старых соединений перед стартом задачи
        close_old_connections()

        self.setup_task(*args, **kwargs)  # Установить параметры задачи

        try:
            self.generate_data()  # Генерация данных для выполнения задачи

            # Если не получены данные таска - прекращаем таск
            if not self.task_data:
                self._send_task_result(
                    message="No data found", progress=100, save_log=True
                )
                self.logger.error(f"Task {self.task_id} completed with no data")
                return self.result

            # Запускаем многопоточно основной цикл таска
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(len(self.task_data), 10)
            ) as executor:
                future_to_data = {
                    executor.submit(self._process_task_iteration, data): data
                    for data in self.task_data
                }
                for future in concurrent.futures.as_completed(future_to_data):
                    try:
                        result = future.result()
                        if not result:
                            self.logger.error(
                                f"Task {self.task_id} completed with errors"
                            )

                        # Если таск без внутреннего многопоточного процесса был отменён
                        # Отменяем все незапущенные задачи
                        if self.is_stopped:
                            for f in future_to_data.keys():
                                f.cancel()

                    except concurrent.futures.TimeoutError:
                        self.logger.error("Timeout error for get result in run_task")
                        continue
                    except Exception as exc:
                        self.logger.error(f"Task generated an exception: {exc}")

        except Exception as e:
            self.logger.error(f"Error during task {self.task_id}: {e}")
        finally:
            # Закрытие старых соединений по окончанию задачи
            # close_old_connections()

            # Принудительно вызываем сборщик мусора
            # gc.collect()

            # Отправляем юзеру уведомление завершения таска
            msg = (f"Задача {str(self.name)} [{truncate_id(self.task_id)}] завершена. \n"
                   f"Обработано: {self.total_iterations} \n"
                   f"Успешных: {self.count_success} \n"
                   f"Неудачных: {self.count_failed}")
            send_notification_to_user.delay(self.user_id, msg)

            # Финальный статус WebSocket
            self._send_task_result(message="Completed", progress=100, save_log=True, process_type="process_finished")

        return self.result

    def setup_task(self, *args, **kwargs):
        """
        Инициализация параметров задачи.
        Переопределяется в дочерних классах при необходимости.
        """
        self.task_id = self.request.id
        self.group_name = f"group_{self.task_id}"
        self.user_id = kwargs.get("user_id")
        self.user = User.objects.filter(id=kwargs.get("user_id")).first()

    def generate_data(self):
        """
        Генерация данных для выполнения задачи.
        Переопределяется в дочерних классах.
        """
        raise NotImplementedError(
            "Method 'generate_data' must be implemented in subclass"
        )

    def verification(self, data):
        """
        Проверяет данные перед выполнением первой итерации.
        """
        if not self.task_id or not self.group_name or not self.user or not data:
            return False
        return True

    def internal_verification(self, *args, **kwargs):
        """
        Проверяет данные перед выполнением действия.
        """
        raise NotImplementedError(
            "Method 'internal_verification' must be implemented in subclass"
        )

    def action_runer(self, data) -> bool | None:
        """
        Основная логика выполнения действия.
        Переопределяется в дочерних классах.
        """
        raise NotImplementedError(
            "Method 'action_runer' must be implemented in subclass"
        )

    def check_skipped_rules(self, *args, **kwargs) -> Optional[bool]:
        """
        Проверяем что таск не отменён клиентов
        Если отменён то отправляем сообщение на клиент и возвращаем True
        """
        if AsyncResult(self.task_id).state == "REVOKED":
            self._send_task_result(
                process_type="task_canceled",
                message=f"Task {self.task_id} was revoked by user.",
                save_log=True,
            )
            return True
        return None

    def _process_task_iteration(self, data):
        """
        Обрабатывает одну итерацию задачи.
        Возвращает True если успешно, или False при неудаче.
        """
        if self.verification(data):
            return self.action_runer(data)
        else:
            self.logger.error(f"Data verification failed: {data}")
            return False

    def check_account_session_error(
        self, response: OFAuthAPIClientResponse | None, account: Account
    ) -> None:
        if account and response and response.success is not True:
            self.logger.error(
                f"CHECK ACCOUNT SESSION ERROR: {response.get_text_error()} Account: {account.username}"
            )
            notification_type = None

            if error_msg := response.get_text_error():
                # Обёртка в транзакцию для надёжной обработки
                with transaction.atomic():
                    if error_msg == NotificationType.ACCESS_DENIED.label:
                        notification_type = NotificationType.ACCESS_DENIED
                    if error_msg == NotificationType.UNKNOWN_ACCESS_DENIED.label:
                        notification_type = NotificationType.UNKNOWN_ACCESS_DENIED

                    if error_msg == NotificationType.WRONG_USER.label:
                        notification_type = NotificationType.WRONG_USER

                    if error_msg == NotificationType.FAIL_FETCH_SESSION.label:
                        notification_type = NotificationType.FAIL_FETCH_SESSION

                    if error_msg == NotificationType.VERIFICATION_ACCOUNT_ERROR.label:
                        notification_type = NotificationType.VERIFICATION_ACCOUNT_ERROR

                    if error_msg == NotificationType.PAID_SUBSCRIPTION_ERROR.label:
                        notification_type = NotificationType.PAID_SUBSCRIPTION_ERROR

                    if error_msg == NotificationType.RESTRICTED_WORDS.label:
                        notification_type = NotificationType.RESTRICTED_WORDS

                    # Получаем или создаём уведомление для данного аккаунта и типа
                    if notification_type:
                        notification, _ = AccountNotification.objects.get_or_create(
                            account=account,
                            notification_type=notification_type,
                            task_id=self.task_id,
                            defaults={"counter": 1},
                        )
                        # Увеличиваем счётчик или сбрасываем его
                        notification.increment_or_reset()

    def _send_task_result(
        self,
        message="",
        iteration=None,
        success_iteration=None,
        error_iteration=None,
        progress=None,
        message_error="",
        process_type="process_update",
        data=None,
        save_log=False,
    ):
        self.result = {
            "type": process_type,
            "message": message,
            "message_error": message_error,
            "progress": (
                progress
                if progress
                else (
                    int((self.progress / self.dynamic_total_steps) * 100)
                    if self.dynamic_total_steps > 0
                    else 0
                )
            ),
            "iteration": iteration if iteration else self.total_iterations,
            "success_iteration": (
                success_iteration if success_iteration else self.count_success
            ),
            "error_iteration": (
                error_iteration if error_iteration else self.count_failed
            ),
            "data": data if data else None,
        }
        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            self.result,
        )

        # Создаем новую запись в таблице Archive
        if (message_error or message) and self.user and save_log:
            self.save_log()

    def send_finally_iteration_result(self, executor, list_data, index):
        self.progress += 1
        self.total_iterations += 1
        self._send_task_result(
            progress=int((self.progress / self.dynamic_total_steps) * 100), process_type="process_finished"
        )

        if self.check_skipped_rules(list_data, index):
            executor.shutdown(wait=False, cancel_futures=True)
            self.cancel_flag.set()  # Устанавливаем флаг отмены
            return False
        return None

    def save_log(self):
        try:
            Archive.objects.create(
                user=self.user,
                task_id=self.task_id,
                message=self.result.get("message", self.result.get("message_error")),
                status=not bool(self.result.get("message_error")),
                additional=self.result.get("data", {}),
            )
        except Exception as e:
            self.logger.error(f"Failed to create archive record: {e}")

    def stop_task(self):
        # Прерываем если была команда с фронта
        if AsyncResult(self.task_id).state == "REVOKED":
            self.is_stopped = True
            self._send_task_result(
                process_type="task_canceled",
                message=f"Task {self.task_id} was revoked by user.",
                save_log=True,
            )

    def _check_internal_response(
        self,
        response: Optional[InternalVerificationResponse | OFAuthAPIClientResponse],
        target: Optional[dict],
        error_msg: str = "Error verification target",
        save_invalid_target: bool = False,
    ) -> bool:
        if not response or response.success is not True:
            self.count_failed += 1
            msg = response.get_text_error() if response else error_msg
            self._send_task_result(
                message=msg,
                save_log=True,
            )

            skipped_types = get_invalid_target_skipped_types()

            if save_invalid_target and msg not in skipped_types and target:
                InvalidTarget.objects.update_or_create(
                    username=target.get("username"),
                    of_id=target.get("id"),
                    defaults={"desc": msg},
                )

            if isinstance(response, InternalVerificationResponse) and target:
                if (
                    response
                    and response.save_invalid_target
                    and msg not in skipped_types
                ):
                    InvalidTarget.objects.update_or_create(
                        username=target.get("username"),
                        of_id=target.get("id"),
                        defaults={"desc": msg},
                    )

            return True

        return False


def truncate_id(task_id, length=5):
    if len(task_id) <= (length * 2 + 3):
        return task_id
    return f"{task_id[:length]}...{task_id[-length:]}"

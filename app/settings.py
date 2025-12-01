import os
import sys
from datetime import timedelta
from pathlib import Path
import environ
import dj_database_url


env = environ.Env(DEBUG=(bool, False))


def str_to_bool(value):
    return str(value).lower() in ("true", "1", "t", "yes")


# Чтение файла .env
environ.Env.read_env()

TATUM_BASE_URL = os.getenv("TATUM_BASE_URL", default="https://api.tatum.io/v3")
TATUM_API_KEY = os.getenv("TATUM_API_KEY", default=None)
TATUM_WEBHOOK_URL = os.getenv("TATUM_WEBHOOK_URL", default=None)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", default=None)

FRONTEND_URL = os.getenv("FRONTEND_URL", default="https://app.ofapp.tech")

# Настройки для использования SMTP сервера
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", default=None)
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", default=None)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", default=None)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = str_to_bool(os.getenv("DEBUG", default=False))

AUTH_USER_MODEL = "authenticate.User"
REST_FRAMEWORK = {
    # 'DEFAULT_PERMISSION_CLASSES': (
    #     'rest_framework.permissions.IsAuthenticated',
    # ),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        # "authenticate.services.async_jwt.AsyncJWTAuthentication"
    ),
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=300),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(hours=8),
    "SLIDING_TOKEN_LIFETIME": timedelta(days=7),
    "SLIDING_TOKEN_REFRESH_LIFETIME_LATE_USER": timedelta(hours=8),
    "SLIDING_TOKEN_LIFETIME_LATE_USER": timedelta(days=7),
}

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "django_extensions",
    "channels",
    "django_celery_beat",
    "websocket.apps.WebsocketConfig",
    "authenticate.apps.AuthenticateConfig",
    "client.apps.ClientConfig",
    "wallet.apps.WalletConfig",
    "notification.apps.NotificationConfig",
    "webhook.apps.WebhookConfig"
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
]

ROOT_URLCONF = "app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# WSGI_APPLICATION = 'app.wsgi.application'
ASGI_APPLICATION = "app.asgi.application"

# Настраиваем каналы Redis
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                os.getenv("REDIS_URL", "redis://localhost:6379")
            ],  # Адрес сервера Redis
            "capacity": 1500,
            "expiry": 7200,  # 2 часа
        },
    },
}

# Настройки для WebSocket
WEBSOCKET_CONNECT_TIMEOUT = 3600  # 1 час
WEBSOCKET_READ_TIMEOUT = 3600     # 1 час
WEBSOCKET_WRITE_TIMEOUT = 3600    # 1 час


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL", default=None),
        conn_max_age=600,  # время жизни соединения (в секундах)
        ssl_require=False,
    )
}
if 'test' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',  # Использование SQLite в памяти для тестов
        }
    }



# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "ru"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

# Укажите абсолютный путь к директории для статиков
STATIC_ROOT = BASE_DIR / "staticfiles"  # Папка для собранных файлов

STATIC_URL = "/static/"
# STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_DIRS = []


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "https://app.wallethub.tech",
    'https://healthcheck.railway.app',
]

# Для работы с WebSocket, Channels требует специальных настроек в ASGI
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "https://backend.wallethub.tech",
    "https://app.wallethub.tech",
    'https://healthcheck.railway.app',
]

CORS_ALLOW_CREDENTIALS = True


# Используйте, если вы работаете через HTTPS
CSRF_COOKIE_SECURE = str_to_bool(os.getenv("CSRF_COOKIE_SECURE", default=True))

# Используйте, если вы работаете через HTTPS
SESSION_COOKIE_SECURE = str_to_bool(os.getenv("SESSION_COOKIE_SECURE", default=True))

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Настройки Celery
CELERY_BROKER_URL = os.getenv("REDIS_URL", default="redis://localhost:6379/0")

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"

CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_RESULT_EXTENDED = True
CELERY_TASK_TRACK_STARTED = True  # Актуально для более новых версий Celery

# Разрешить запись статуса PENDING (поскольку записи задачи могут создаваться при старте)
CELERY_TASK_IGNORE_RESULT = False

# Воркеры
CELERY_WORKER_CONCURRENCY = 8  # Сколько задач одновременно могут выполняться
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Минимизировать задержки в долгих задачах

# Логика перезапуска воркеров после определённого кол-ва задач
CELERYD_MAX_TASKS_PER_CHILD = 60

# Отвечает за период запуска задачи celery.backend_cleanup
CELERY_RESULT_EXPIRES = timedelta(days=30)  # Результаты будут храниться 30 дней

DJANGO_CELERY_RESULTS_TASK_ID_MAX_LENGTH=191


REDIS_OPTIONS = {
    "socket_connect_timeout": 10,  # Тайм-аут подключения
    "socket_keepalive": True,  # Поддержание соединений
    "retry_on_timeout": True,  # Повторы при разрыве соединения
}


INSTALLED_APPS += ["django_celery_results"]

LOGIN_REDIRECT_URL = "/admin/"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {pathname}:{lineno} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",  # Используем цветной форматтер
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",  # Уровень логирования
            "propagate": True,  # Если `True`, логи будут передаваться другим логгерам выше в иерархии
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

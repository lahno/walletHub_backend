web: python manage.py collectstatic --no-input && uvicorn app.asgi:application --host 0.0.0.0 --port $PORT
worker: celery -A app worker --loglevel=info -E
beat: celery -A app beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
bot: python -m bot.main
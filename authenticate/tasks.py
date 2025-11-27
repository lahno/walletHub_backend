from celery import shared_task
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings


@shared_task
def send_welcome_email_task(user_email, username):
    # Отправка приветственного сообщения юзерам из админки
    context = {"username": username, "frontend_url": settings.FRONTEND_URL}
    html_message = render_to_string("emails/welcome.html", context)

    email = EmailMessage(
        subject="Добро пожаловать!",
        body=html_message,
        from_email=settings.EMAIL_HOST_USER,
        to=[user_email],
    )
    email.content_subtype = "html"
    email.send()

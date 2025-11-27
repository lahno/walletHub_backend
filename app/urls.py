"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views.py. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views.py
    1. Add an import:  from my_app import views.py
    2. Add a URL to urlpatterns:  path('', views.py.home, name='home')
Class-based views.py
    1. Add an import:  from other_app.views.py import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include

from app.view import get_last_commit

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/get-version/', get_last_commit, name='get-version'),
    path("api/", include("authenticate.urls")),
    path("api/client/", include("client.urls")),
    path("api/wallet/", include("wallet.urls")),
    path("api/webhook/", include("webhook.urls")),
]

from django.urls import path

from dashboard.views import dashboard
from django.conf import settings

urlpatterns = [
    path("", dashboard, name=settings.LOGIN_REDIRECT_URL),
]

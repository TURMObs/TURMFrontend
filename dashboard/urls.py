from django.urls import path

from dashboard.views import (
    dashboard,
    delete_all,
    upload_observation,
    update_observation,
)
from django.conf import settings

urlpatterns = [
    path("", dashboard, name=settings.LOGIN_REDIRECT_URL),
    path("delete-observations/", delete_all),
    path("upload-observations/", upload_observation),
    path("update-observations/", update_observation),
]

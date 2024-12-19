from django.urls import path

from django.conf import settings

from dsgvo.views import index, delete_user, get_user_data

urlpatterns = [
    path("", index, name=settings.DSGVO_URL),
    path("delete-user/", delete_user, name="delete_user"),
    path("get-user-data/", get_user_data, name="get_user_data"),
]

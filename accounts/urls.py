from django.contrib.auth.views import LogoutView
from django.urls import path
from django.conf import settings

from accounts.views import (
    generate_invitation,
    generate_user_invitation,
    login,
    login_user,
    register,
    register_user,
    delete_user,
    get_user_data,
    dsgvo_options,
    delete_invitation,
)

urlpatterns = [
    path("login", login, name="login"),
    path("login_user", login_user, name="login-user"),
    path(
        "logout",
        LogoutView.as_view(next_page=settings.LOGOUT_REDIRECT_URL),
        name="logout",
    ),
    path(
        "generate-invitation",
        generate_invitation,
        name="generate-invitation",
    ),
    path(
        "generate-invitation/create",
        generate_user_invitation,
        name="generate-user-invitation",
    ),
    path("register/<uuid:token>", register),
    path("register/<uuid:token>/signup", register_user, name="signup"),
    path(
        "delete_invitation/<int:invitation_id>",
        delete_invitation,
        name="delete-invitation",
    ),
    path("delete-user/<int:user_id>", delete_user, name="delete-user"),
    path("get-user-data", get_user_data, name="get-user-data"),
    path("dsgvo", dsgvo_options, name=settings.DSGVO_URL),
]

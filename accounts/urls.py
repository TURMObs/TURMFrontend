from django.contrib.auth.views import LogoutView
from django.urls import path
from django.conf import settings

from accounts.views import (
    user_management,
    generate_user_invitation,
    login,
    login_user,
    register,
    register_user,
    get_user_data,
    dsgvo_options,
    delete_invitation,
    has_invitation,
    edit_user,
    delete_user,
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
        "user-management",
        user_management,
        name="user-management",
    ),
    path(
        "user-management/create-invitation",
        generate_user_invitation,
        name="generate-user-invitation",
    ),
    path("register/<uuid:token>", register),
    path("register/<uuid:token>/signup", register_user, name="signup"),
    path("has-invitation", has_invitation, name="has-invitation"),
    path(
        "delete-invitation/<int:invitation_id>",
        delete_invitation,
        name="delete-invitation",
    ),
    path("edit-user", edit_user, name="edit-user"),
    path("get-user-data", get_user_data, name="get-user-data"),
    path("dsgvo", dsgvo_options, name=settings.DSGVO_URL),
    path("has-invitation", has_invitation, name="has-invitation"),
    path(
        "delete-invitation/<int:invitation_id>",
        delete_invitation,
        name="delete-invitation",
    ),
    path("delete-user/<int:user_id>", delete_user, name="delete-user"),
]

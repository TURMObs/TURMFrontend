from django.contrib.auth.views import LogoutView
from django.urls import path

from authentication.views import (
    generate_invitation,
    generate_user_invitation,
    login,
    login_user,
    register,
    register_user,
)

urlpatterns = [
    path("", login, name="index"),
    path("login", login_user, name="login"),
    path("logout/", LogoutView.as_view(next_page="index"), name="logout"),
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
    path("register/<uuid:token>/", register),
    path("register/<uuid:token>/signup", register_user, name="signup"),
]

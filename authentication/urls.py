from django.contrib.auth.views import LogoutView
from django.urls import path

from authentication.views import generate_invitation, index, register

urlpatterns = [
    path("", index, name="index"),
    path("logout/", LogoutView.as_view(next_page="index"), name="logout"),
    path(
        "generate-invitation",
        generate_invitation,
        name="generate-invitation",
    ),
    path("register/<uuid:token>/", register, name="register_from_invitation"),
]

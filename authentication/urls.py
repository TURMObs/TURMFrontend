from django.urls import path
from authentication.views import index, generate_invitation_link, register
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path("", index, name="index"),
    path("logout/", LogoutView.as_view(next_page="index"), name="logout"),
    path(
        "generate-invitation-link",
        generate_invitation_link,
        name="generate-invitation-link",
    ),
    path("register/<uuid:token>/", register, name="register_from_invitation"),
]

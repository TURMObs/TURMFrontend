from django.urls import path
from authentication.views import index, generate_invitation_link

urlpatterns = [
    path("", index, name="index"),
    path("generate-invitation-link", generate_invitation_link, name="generate-invitation-link"),
]

from django.urls import path
from authentication.views import index, generate_invitation_link, register

urlpatterns = [
    path("", index, name="index"),
    path("generate-invitation-link", generate_invitation_link, name="generate-invitation-link"),
    path('register/<uuid:token>/', register, name='register_from_invitation'),
]

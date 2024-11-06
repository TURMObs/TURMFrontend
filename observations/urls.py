from django.urls import path

from observations.views import create_observation

urlpatterns = [
    path("create/", create_observation),
]

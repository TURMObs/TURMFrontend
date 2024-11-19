from django.urls import path

from observation_data.views import create_observation

urlpatterns = [
    path("create/", create_observation),
]

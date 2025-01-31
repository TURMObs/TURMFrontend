from django.urls import path

from observation_data.views import create_observation, edit_observation

urlpatterns = [
    path("create/", create_observation),
    path(
        "edit/<int:observation_id>",
        edit_observation,
    ),
]

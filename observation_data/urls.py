from django.urls import path

from observation_data.views import (
    create_observation,
    delete_observation,
    edit_observation,
    finish_observation,
)

urlpatterns = [
    path("create/", create_observation),
    path("delete/<int:observation_id>", delete_observation, name="delete-observation"),
    path(
        "edit/<int:observation_id>",
        edit_observation,
    ),
    path("finish/<int:observation_id>", finish_observation, name="finish-observation"),
]

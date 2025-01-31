from django.urls import path

from observation_request.views import (
    create_observation_request,
    edit_observation_request,
)

urlpatterns = [
    path("create", create_observation_request, name="create-observation-request"),
    path(
        "edit/<int:observation_id>",
        edit_observation_request,
        name="edit-observation-request",
    ),
]

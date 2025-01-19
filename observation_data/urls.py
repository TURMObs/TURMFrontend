from django.urls import path

from observation_data.views import create_observation, delete_observation

urlpatterns = [
    path("create/", create_observation),
    path("delete/<int:observation_id>/", delete_observation),
]

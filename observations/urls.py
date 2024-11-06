from django.urls import path

from interactiveTest.views import input_test, create_json
from observations.views import create_observation

urlpatterns = [
    path("create/", create_observation),
]

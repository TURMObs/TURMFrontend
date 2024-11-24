from django.urls import path

from observation_data.views import create_observation
from observation_request.views import *

urlpatterns = [
    path("", simple_request),
    path("test/", test_request),
]

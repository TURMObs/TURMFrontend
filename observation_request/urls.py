from django.urls import path

from observation_request.views import *

urlpatterns = [
    path("", simple_request),
]

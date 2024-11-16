from django.urls import path

from observationRequest.views import *

urlpatterns = [
    path("", simple_request),
]

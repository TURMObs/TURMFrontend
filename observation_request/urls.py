from django.urls import path

from observation_request.views import simple_request, test_request

urlpatterns = [
    path("", simple_request),
    path("test/", test_request),
]

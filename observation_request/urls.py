from django.urls import path

from observation_request.views import simple_request, test_request

urlpatterns = [
    path("", simple_request, name="observation-request"),
    path("test/", test_request),
]

from django.urls import path

from interactiveTest.views import input_test, create_json

urlpatterns = [
    path('', input_test),
    path('createjson/', create_json)
]
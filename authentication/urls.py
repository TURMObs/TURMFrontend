from django.urls import path
from authentication.views import index

urlpatterns = [
    path("", index),
]

from django.urls import path
from root.views import index

urlpatterns = [
    path("", index),
]

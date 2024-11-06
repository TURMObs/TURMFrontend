import json

from django.shortcuts import render
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from observations.serializers import ExoplanetObservationSerializer


# Create your views here.


@api_view(["POST"])
def create_observation(request):
    serializer = ExoplanetObservationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

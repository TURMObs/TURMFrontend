from django.shortcuts import render
from observation_data.models import AbstractObservation


def dashboard(request):
    observations = AbstractObservation.objects.all()

    return render(request, "dashboard/index.html", {"observations": observations})

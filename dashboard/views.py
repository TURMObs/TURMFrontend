from django.shortcuts import render
from observation_data.models import AbstractObservation


def dashboard(request):
    if request.user.is_superuser:
        observations = AbstractObservation.objects.all()
    else:
        observations = AbstractObservation.objects.filter(user=request.user)

    return render(request, "dashboard/index.html", {"observations": observations})

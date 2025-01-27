from django.core.management import call_command
from django.shortcuts import render, redirect
from observation_data.models import AbstractObservation


def dashboard(request):
    if request.user.is_superuser:
        observations = AbstractObservation.objects.all()
    else:
        observations = AbstractObservation.objects.filter(user=request.user)

    return render(request, "dashboard/index.html", {"observations": observations})

def delete_all(request):
    AbstractObservation.objects.all().delete()
    return redirect("dashboard")

def upload_observation(request):
    call_command("upload_observations")
    return redirect("dashboard")

def update_observation(request):
    call_command("update_observations")
    return redirect("dashboard")
import os
import nextcloud.nextcloud_manager as nm
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

    prefix = os.getenv("NC_PREFIX", default="")

    if prefix:
        nm.delete(prefix)
    else:
        nm.delete("TURMX")
        nm.delete("TURMX2")

    return redirect("dashboard")


def upload_observation(request):
    nm.initialize_connection()
    prefix = os.getenv("NC_PREFIX", default="")

    path1 = "TURMX/Projects/"
    path2 = "TURMX2/Projects/"
    if prefix:
        path1 = f"{prefix}/{path1}"
        path2 = f"{prefix}/{path2}"

    nm.mkdir(path1)
    nm.mkdir(path2)

    call_command("upload_observations")
    return redirect("dashboard")


def update_observation(request):
    call_command("update_observations")
    return redirect("dashboard")

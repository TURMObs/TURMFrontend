from django.shortcuts import render

from accounts.models import UserPermission
from observation_data.models import AbstractObservation


def dashboard(request):
    if request.user.has_perm(UserPermission.CAN_SEE_ALL_OBSERVATIONS):
        observations = AbstractObservation.objects.all()
    else:
        observations = AbstractObservation.objects.filter(user=request.user)

    return render(request, "dashboard/index.html", {"observations": observations})

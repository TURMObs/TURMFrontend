from django.shortcuts import render

from accounts.models import UserPermission
from observation_data.models import (
    AbstractObservation,
    ObservationStatus,
    ObservationType,
)


def dashboard(request):
    if request.user.has_perm(UserPermission.CAN_SEE_ALL_OBSERVATIONS):
        observations = AbstractObservation.objects.all()
    else:
        observations = AbstractObservation.objects.filter(user=request.user)

    active_observations = observations.exclude(
        project_status=ObservationStatus.COMPLETED
    ).order_by("created_at")
    completed_observations = observations.filter(
        project_status=ObservationStatus.COMPLETED
    ).order_by("created_at")

    return render(
        request,
        "dashboard/index.html",
        {
            "active_observations": active_observations,
            "completed_observations": completed_observations,
            "ObservationStatus": ObservationStatus,
            "ObservationType": ObservationType,
        },
    )

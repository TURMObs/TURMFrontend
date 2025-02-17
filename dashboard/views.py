from django.db.models import Q
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

    completed_observations = observations.filter(
        Q(project_status=ObservationStatus.COMPLETED)
        | Q(project_status=ObservationStatus.ERROR)
        | Q(project_status=ObservationStatus.FAILED)
        | Q(project_status=ObservationStatus.PENDING_DELETION)
    ).order_by("-created_at")

    active_observations = observations.filter(
        ~Q(id__in=completed_observations.values_list("id", flat=True))
    ).order_by("-created_at")

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

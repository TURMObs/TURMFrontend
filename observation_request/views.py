from django.shortcuts import redirect, render

from TURMFrontend import settings
from observation_data.forms import (
    CelestialTargetForm,
    ExposureSettingsForm,
    TURMProjectForm,
)
from observation_data.models import AbstractObservation, ObservationType
from observation_data.serializers import get_serializer


def create_observation_request(request):
    context = {
        "forms": [
            ("Project", TURMProjectForm()),
            ("Target", CelestialTargetForm()),
            ("Exposure", ExposureSettingsForm()),
        ],
        "create_form_url": settings.SUBPATH + "/observation-data/create/",
    }
    return render(
        request, "observation_request/create_observation_template.html", context
    )


def edit_observation_request(request, observation_id):
    observation = AbstractObservation.objects.filter(id=observation_id).first()
    if observation is None:
        return redirect(settings.LOGIN_REDIRECT_URL)

    serializer = get_serializer(observation.observation_type)
    data = serializer.to_representation(serializer, observation)
    print(data)

    observation_type = ObservationType(observation.observation_type)

    context = {
        "forms": [
            (
                "Project",
                TURMProjectForm(initial={"observatory": observation.observatory}),
            ),
            (
                "Target",
                CelestialTargetForm(
                    initial={
                        "name": observation.target.name,
                        "catalog_id": observation.target.catalog_id,
                        "ra": observation.target.ra,
                        "dec": observation.target.ra,
                    }
                ),
            ),
            (
                "Exposure",
                ExposureSettingsForm(
                    initial={
                        "observation_type": (
                            observation_type,
                            observation_type.label,
                        ),
                        "filter_set": print(
                            [ft.filter_type for ft in observation.filter_set.all()]
                        ),
                        "exposure_time": observation.exposure_time,
                    }
                ),
            ),
        ],
        "edit_form_url": settings.SUBPATH + "/observation-data/edit/",
    }
    return render(
        request, "observation_request/edit_observation_template.html", context
    )

from django.shortcuts import redirect, render
import json

from TURMFrontend import settings
from accounts.models import ObservatoryUser, UserPermission
from observation_data import forms
from observation_data.forms import (
    CelestialTargetForm,
    ExposureSettingsForm,
    TURMProjectForm,
    ExpertExposureSettingsForm,
)
from observation_data.models import AbstractObservation, ObservationType


def create_observation_request(request):
    if isinstance(request.user, ObservatoryUser) and request.user.has_perm(
        UserPermission.CAN_CREATE_EXPERT_OBSERVATION
    ):
        exposure_form = ExpertExposureSettingsForm()
    else:
        exposure_form = ExposureSettingsForm()

    context = {
        "forms": [
            ("Observatory", TURMProjectForm()),
            ("Target", CelestialTargetForm()),
            ("Exposure", exposure_form),
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

    existing_request = build_observation_data(observation)

    if isinstance(request.user, ObservatoryUser) and request.user.has_perm(
        UserPermission.CAN_CREATE_EXPERT_OBSERVATION
    ):
        exposure_form = ExpertExposureSettingsForm()
    else:
        exposure_form = ExposureSettingsForm()

    context = {
        "forms": [
            ("Observatory", TURMProjectForm()),
            ("Target", CelestialTargetForm()),
            ("Exposure", exposure_form),
        ],
        "edit_form_url": settings.SUBPATH
        + "/observation-data/edit/"
        + str(observation_id),
        "existing_request": json.dumps(existing_request),
    }
    return render(
        request, "observation_request/edit_observation_template.html", context
    )


def build_observation_data(observation: AbstractObservation):
    content = {
        "observatory": observation.observatory.name,
        "observation_type": observation.observation_type,
        "filter_set": [ft.filter_type for ft in observation.filter_set.all()],
        "target_name": observation.target.name,
        "catalog_id": observation.target.catalog_id,
        "ra": observation.target.ra,
        "dec": observation.target.dec,
        "exposure_time": float(observation.exposure_time),
    }

    match observation.observation_type:
        case ObservationType.IMAGING:
            content["frames_per_filter"] = observation.frames_per_filter
        case ObservationType.EXOPLANET:
            content["start_observation"] = (
                str(observation.start_observation.replace(tzinfo=None)).strip(),
            )
            content["end_observation"] = (
                str(observation.end_observation.replace(tzinfo=None)).strip(),
            )
        case ObservationType.VARIABLE:
            content["frames_per_filter"] = observation.frames_per_filter
            content["minimum_altitude"] = float(observation.minimum_altitude)
        case ObservationType.MONITORING:
            content["frames_per_filter"] = observation.frames_per_filter
            content["minimum_altitude"] = float(observation.minimum_altitude)
            content["start_scheduling"] = (
                str(observation.start_scheduling).strip()[:10],
            )
            content["end_scheduling"] = (str(observation.end_scheduling).strip()[:10],)
            content["cadence"] = observation.cadence
        case ObservationType.EXPERT:
            content["frames_per_filter"] = observation.frames_per_filter
            content["dither_every"] = observation.dither_every
            content["binning"] = observation.binning
            content["subframe"] = float(observation.subframe)
            content["gain"] = observation.gain
            content["offset"] = observation.offset
            content["batch_size"] = observation.batch_size
            content["minimum_altitude"] = float(observation.minimum_altitude)
            content["moon_separation_angle"] = float(observation.moon_separation_angle)
            content["moon_separation_width"] = observation.moon_separation_width
            content["priority"] = observation.priority
            if observation.start_scheduling:
                content["start_scheduling"] = (
                    str(observation.start_scheduling).strip()[:10],
                )
                content["end_scheduling"] = (
                    str(observation.end_scheduling).strip()[:10],
                )
                content["cadence"] = observation.cadence
                if observation.start_observation_time:
                    content["start_observation_time"] = str(
                        observation.start_observation_time
                    )[:5]
                    content["end_observation_time"] = str(
                        observation.end_observation_time
                    )[:5]
                    content["schedule_type"] = forms.SchedulingType.SCHEDULE_TIME.name
                else:
                    content["schedule_type"] = forms.SchedulingType.SCHEDULE.name
            elif observation.start_observation:
                content["start_observation"] = (
                    str(observation.start_observation.replace(tzinfo=None)).strip(),
                )
                content["end_observation"] = (
                    str(observation.end_observation.replace(tzinfo=None)).strip(),
                )
                content["schedule_type"] = forms.SchedulingType.TIMED.name
            else:
                content["schedule_type"] = forms.SchedulingType.NO_CONSTRAINT.name
    return content

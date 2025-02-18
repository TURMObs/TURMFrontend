from django.shortcuts import redirect, render
import json
from TURMFrontend import settings
from observation_data import forms
from observation_data.forms import (
    CelestialTargetForm,
    ExposureSettingsForm,
    TURMProjectForm,
)
from observation_data.models import AbstractObservation, ObservationType


def create_observation_request(request):
    context = {
        "forms": [
            ("Observatory", TURMProjectForm()),
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

    existing_request = build_observation_data(observation)

    context = {
        "forms": [
            ("Observatory", TURMProjectForm()),
            ("Target", CelestialTargetForm()),
            ("Exposure", ExposureSettingsForm()),
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
    }

    if observation.observation_type == ObservationType.EXPERT:
        if observation.start_scheduling:
            if observation.start_observation_time:
                content["schedule_type"] = forms.SchedulingType.SCHEDULE_TIME.name
            else:
                content["schedule_type"] = forms.SchedulingType.SCHEDULE.name
        elif observation.start_observation:
            content["schedule_type"] = forms.SchedulingType.TIMED.name
        else:
            content["schedule_type"] = forms.SchedulingType.NO_CONSTRAINT.name

    if observation.observation_type in [
        ObservationType.IMAGING,
        ObservationType.EXOPLANET,
        ObservationType.VARIABLE,
        ObservationType.MONITORING,
        ObservationType.EXPERT,
    ]:
        content["exposure_time"] = float(observation.exposure_time)

    if observation.observation_type in [
        ObservationType.IMAGING,
        ObservationType.VARIABLE,
        ObservationType.MONITORING,
        ObservationType.EXPERT,
    ]:
        content["frames_per_filter"] = observation.frames_per_filter

    if observation.observation_type in [
        ObservationType.EXOPLANET,
        ObservationType.EXPERT,
    ]:
        if observation.start_observation:
            content["start_observation"] = (
                str(observation.start_observation.replace(tzinfo=None)).strip(),
            )
            content["end_observation"] = (
                str(observation.end_observation.replace(tzinfo=None)).strip(),
            )

    match observation.observation_type:
        case ObservationType.VARIABLE:
            content["minimum_altitude"] = float(observation.minimum_altitude)

        case ObservationType.EXPERT:
            content["priority"] = observation.priority
            content["dither_every"] = observation.dither_every
            content["subframe"] = float(observation.subframe)
            content["binning"] = observation.binning
            content["gain"] = observation.gain
            content["offset"] = observation.offset
            content["moon_separation_angle"] = float(observation.moon_separation_angle)
            content["moon_separation_width"] = observation.moon_separation_width
            content["minimum_altitude"] = float(observation.minimum_altitude)

    if observation.observation_type in [
        ObservationType.MONITORING,
        ObservationType.EXPERT,
    ]:
        if observation.start_scheduling:
            content["start_scheduling"] = (
                str(observation.start_scheduling).strip()[:10],
            )
            content["end_scheduling"] = (
                str(observation.end_scheduling).strip()[:10],
            )
            content["cadence"] = observation.cadence

    return content

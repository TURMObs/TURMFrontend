from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view

from observation_data.models import ObservationType, Observatory
from observation_data.forms import (
    CelestialTargetForm,
    ExposureForm,
    QueryEnum, WipForm,
)


def simple_request(request):
    context = {}
    # Observation Types
    # list of Name and if they should only be displayed to a super_user
    print(Observatory.objects.first().pk)
    observatories_radio = {
        "options": ((obs.pk, False) for obs in Observatory.objects.all()),
        "hide": "false",
        "name": "observatory",  # todo: change to model meta field name
        "input_selector": "observatory_radio_label",
        "effect_selector": QueryEnum.observatory_dependent.name,
    }
    observation_types_radio = {
        "options": (
            (str(ObservationType.IMAGING), False),
            (str(ObservationType.EXOPLANET), False),
            (str(ObservationType.VARIABLE), False),
            (str(ObservationType.MONITORING), False),
            (str(ObservationType.EXPERT), True),
        ),
        "hide": "true",
        "name": "observation_type",
        "input_selector": "observation_type_radio_label",
        "effect_selector": QueryEnum.observation_type_dependent.name,
    }

    # Forms
    c_forms = [
        ("Project", "", observatories_radio),
        ("Target", CelestialTargetForm(), None),
        ("Exposure", ExposureForm(), observation_types_radio),
        ("", WipForm(), None),
    ]
    context["forms"] = c_forms

    # endpoint url
    context['create_form_url'] = '../observation-data/create/'

    return render(request, "observationRequest/requestTemplate.html", context)


@require_POST
@api_view(["POST"])
def test_request(request):
    return HttpResponse(request.data.dict())

from django.db.models import ForeignKey
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view

from observation_data.models import ObservationType, Observatory, AbstractObservation, ExpertObservation
from observation_data.forms import (
    CelestialTargetForm,
    ExposureForm,
    QueryEnum, WipForm, ExposureSettingsForm, TRUMProjectForm
)


def _simple_request(request):
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

def simple_request(request):
    context = {}
    # Forms
    forms = [
        ("Project", TRUMProjectForm()),
        ("Target", CelestialTargetForm()),
        ("Exposure", ExposureSettingsForm()),
    ]
    context["forms"] = forms
    context['create_form_url'] = '/observation-request/test/'
    return render(request, "observationRequest/requestTemplateV2.html", context)


@require_POST
@api_view(["POST"])
def test_request(request):
    return HttpResponse(f'<p>"{str(dict(request.data))}"</p>')

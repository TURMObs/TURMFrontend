from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view

from urllib.parse import parse_qs
from observation_data.models import AbstractObservation

# Create your views here.


from observation_data.forms import *


def simple_request(request):
    context = {}
    # Observation Types
    # list of Name and if they should only be displayed to a super_user
    observation_types = (
        (str(AbstractObservation.ObservationType.IMAGING), False),
        (AbstractObservation.ObservationType.EXOPLANET, False),
        (AbstractObservation.ObservationType.VARIABLE, False),
        (AbstractObservation.ObservationType.MONITORING, False),
        (AbstractObservation.ObservationType.EXPERT, True),
    )

    # Forms
    c_forms = [
        ("Project", ProjectForm(), None),
        ("Target", CelestialTargetForm(), None),
        ("Exposure", ExposureForm(), observation_types),
    ]
    context["forms"] = c_forms

    # endpoint url
    # context['create_form_url'] = '../observation_data/create/'
    context["create_form_url"] = "test/"

    return render(request, "observationRequest/requestTemplate.html", context)


@require_POST
@api_view(["POST"])
def test_request(request):
    parsed_data = parse_qs(request.body)
    decoded_data = {
        key.decode("utf-8"): value[0].decode("utf-8")
        for key, value in parsed_data.items()
    }

    return HttpResponse(str(decoded_data))
    # return HttpResponse(request.body)

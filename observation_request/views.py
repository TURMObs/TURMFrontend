from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view

from observation_data.forms import (
    CelestialTargetForm,
    ExposureSettingsForm,
    TURMProjectForm,
)


def simple_request(request):
    context = {}
    # Forms
    forms = [
        ("Project", TURMProjectForm()),
        ("Target", CelestialTargetForm()),
        ("Exposure", ExposureSettingsForm()),
    ]
    context["forms"] = forms
    context["create_form_url"] = "/observation-data/create/"
    return render(request, "observationRequest/requestTemplate.html", context)


@require_POST
@api_view(["POST"])
def test_request(request):
    return HttpResponse(f'<p>"{str(dict(request.data))}"</p>')

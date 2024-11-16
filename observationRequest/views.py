from django.contrib.messages import success
from django.shortcuts import render

from ._toBeRemoved.forms import ExoplanetObservationForm, CelestialTargetForm

from observations.models import CelestialTarget

# Create your views here.

def simple_request(request):
    context = {}
    form_project = ExoplanetObservationForm()
    context['form_project'] = form_project
    form_target = CelestialTargetForm()
    context['form_target'] = form_target

    return render(request, 'observationRequest/requestTemplate.html', context)

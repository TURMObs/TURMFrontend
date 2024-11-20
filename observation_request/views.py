from django.contrib.messages import success
from django.db.models import QuerySet
from django.shortcuts import render

from ._toBeRemoved.forms import ExoplanetObservationForm, CelestialTargetForm

from observations.models import CelestialTarget

# Create your views here.

def simple_request(request):
    context = {}

    forms = [("Project", ExoplanetObservationForm()),
             ('Target', CelestialTargetForm()) ]
    context['forms'] = forms

    return render(request, 'observationRequest/requestTemplateExtends.html', context)

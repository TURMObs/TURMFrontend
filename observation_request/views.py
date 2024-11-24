from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view

from urllib.parse import parse_qs

# Create your views here.


from observation_data.forms import *

def simple_request(request):
    context = {}

    c_forms = [("Project", ProjectForm()),
             ('Target', CelestialTargetForm()),
             ('Exposure', ExposureForm()),]
    context['forms'] = c_forms
    # context['is_super_user'] = request.user.is_superuser
    context['is_super_user'] = True
    context['create_form_url'] = '../observation_data/create/'
    context['create_form_url'] = 'test/'

    return render(request, 'observationRequest/requestTemplate.html', context)

@require_POST
@api_view(["POST"])
def test_request(request):
    parsed_data = parse_qs(request.body)
    decoded_data = {key.decode('utf-8'): value[0].decode('utf-8') for key, value in parsed_data.items()}


    return HttpResponse(str(decoded_data))
    #return HttpResponse(request.body)
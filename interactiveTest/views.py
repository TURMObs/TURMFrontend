import json
import os.path

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST


# Create your views here.


def input_test(request):
    return render(request, "interactiveTest/local_input.html")


@require_POST
def create_json(request):
    print(request.body)
    data = json.loads(request.body)
    print(data)
    path = os.path.join("interactiveTest", "document.json")

    with open(path, "w") as f:
        json.dump(data, f)
    return JsonResponse({"status": "ok"}, status=418)

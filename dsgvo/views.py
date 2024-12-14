from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from TURMFrontend import settings
from authentication.views import logger
from dsgvo import user_data


def index(request):
    return render(request, "dsgvo/index.html")


@require_http_methods(["DELETE"])
def delete_user(request):
    user = request.user
    user_data.delete_user(user)
    logger.info(f"User {user} deleted their account.")
    return JsonResponse({"status": "success"})


def get_user_data(request):
    data = user_data.get_all_data(request.user)
    logger.info(f"User requested their data: {data}")
    return JsonResponse(data)
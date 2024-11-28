from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.status import HTTP_401_UNAUTHORIZED

from observation_data.models import ObservationType
from observation_data.serializers import get_serializer


@require_POST
@api_view(["POST"])
def create_observation(request):
    """
    Create an observation based on the observation type.
    The passed data must include satisfy the is_valid() method of the corresponding serializer.
    Note that the user must be authenticated to create an observation and staff to create an expert observation.
    :param request: HTTP request with observation data
    :return: HTTP response with the created observation data or error message
    """
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required"},
            status=HTTP_401_UNAUTHORIZED,
        )
    request_data = request.data
    request_data["user"] = request.user.id

    if not request_data.get("observation_type"):
        return Response(
            {"error": "Observation type missing"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    observation_type = request_data.get("observation_type")
    if observation_type == ObservationType.EXPERT:
        if not request.user.is_superuser:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN,
            )
    serializer_class = get_serializer(observation_type)
    if not serializer_class:
        return Response(
            {"error": "Invalid observation type"}, status=status.HTTP_400_BAD_REQUEST
        )

    serializer = serializer_class(data=request_data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.status import HTTP_401_UNAUTHORIZED

from observation_data.serializers import (
    ExoplanetObservationSerializer,
    ImagingObservationSerializer,
    VariableObservationSerializer,
    MonitoringObservationSerializer,
    ExpertObservationSerializer,
)


@api_view(["POST"])
def create_observation(request):
    # TODO: Check and test user authentication
    """
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required"},
            status=HTTP_401_UNAUTHORIZED,
        )
    """

    if not request.data.get("observation_type"):
        return Response(
            {"error": "Observation type missing"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    observation_type_to_serializer = {
        "Exoplanet": ExoplanetObservationSerializer,
        "Imaging": ImagingObservationSerializer,
        "Variable": VariableObservationSerializer,
        "Monitoring": MonitoringObservationSerializer,
        "Expert": ExpertObservationSerializer,
    }

    serializer_class = observation_type_to_serializer.get(
        request.data.get("observation_type")
    )
    if not serializer_class:
        return Response(
            {"error": "Invalid observation type"}, status=status.HTTP_400_BAD_REQUEST
        )

    serializer = serializer_class(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    print("not valid: ", serializer.errors)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

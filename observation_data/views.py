import builtins
import logging

from django.core.exceptions import FieldDoesNotExist, BadRequest
from django.db.models import ManyToManyField
from django.http import QueryDict
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.status import HTTP_401_UNAUTHORIZED, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from observation_data.models import ObservationType, AbstractObservation
from accounts.models import ObservatoryUser, UserPermission
from observation_data.serializers import get_serializer
from observation_data.observation_management import delete_observation as delete_observation_command


logger = logging.getLogger(__name__)


@require_POST
@api_view(["POST"])
def create_observation(request):
    """
    Create an observation based on the observation type.
    The passed data must satisfy the is_valid() method of the corresponding serializer and include all necessary fields.
    Note that the user must be authenticated to create an observation and staff to create an expert observation.
    :param request: HTTP request with observation data
    :return: HTTP response with the created observation data or error message
    """

    user = request.user
    if not user.is_authenticated:
        return Response(
            {"error": "Authentication required"},
            status=HTTP_401_UNAUTHORIZED,
        )

    if not isinstance(user, ObservatoryUser):
        return Response(
            {"error": "Invalid user model"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not user.has_quota_left():
        return Response(
            {"error": "Quota exceeded"},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not user.has_lifetime_left():
        return Response(
            {"error": "Lifetime exceeded"},
            status=status.HTTP_403_FORBIDDEN,
        )

    request_data = request.data.copy()
    observation_type = request_data.get("observation_type")

    serializer_class = get_serializer(observation_type)
    if not serializer_class:
        return Response(
            {"error": f"Invalid observation type: {observation_type}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(request.data, QueryDict):
        request_data = convert_query_dict(
            request.data.copy(), serializer_class.Meta.model
        )

    observation_type = request_data.get("observation_type")
    request_data["user"] = request.user.id

    if observation_type == ObservationType.EXPERT:
        if not user.has_perm(UserPermission.CAN_CREATE_EXPERT_OBSERVATION):
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN,
            )

    if "name" in request_data and isinstance(request_data["name"], str):
        request_data = _nest_observation_request(
            request_data,
            {
                "ra": "target.ra",
                "dec": "target.dec",
                "name": "target.name",
                "catalog_id": "target.catalog_id",
            },
        )

    serializer = serializer_class(data=request_data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


def _nest_observation_request(data, mappings):
    """
    Convert flat dictionary to nested structure based on mappings.
    :param data: The flat dictionary.
    :param mappings: A dict mapping flat keys to their nested structure.
    :return: A nested dictionary.
    """
    nested_data = {}
    for flat_key, nested_path in mappings.items():
        value = data.pop(flat_key, None)
        if value is not None:
            keys = nested_path.split(".")
            d = nested_data
            for key in keys[:-1]:
                d = d.setdefault(key, {})
            d[keys[-1]] = value
    nested_data.update(data)
    return nested_data


def convert_query_dict(qdict, model: AbstractObservation):
    converted_dict = {}
    meta = model._meta
    for key, val in dict(qdict).items():
        try:
            meta.get_field(key)
        except FieldDoesNotExist:
            converted_dict[key] = val[0]
            continue
        if len(val) > 1:
            converted_dict[key] = val
            continue
        if isinstance(meta.get_field(key), ManyToManyField):
            converted_dict[key] = val
            continue
        converted_dict[key] = val[0]

    return converted_dict

@require_POST
@api_view(["POST"])
def delete_observation(request):
    user = request.user
    if not user.is_authenticated:
        return Response(
            {"error": "Authentication required"},
            status=HTTP_401_UNAUTHORIZED,
        )

    if not isinstance(user, ObservatoryUser):
        return Response(
            {"error": "Invalid user model"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    request_data = request.data
    observation_id = request_data.get("id")

    if not observation_id:
        return Response(
            {"error": "Invalid observation id"},
            status=HTTP_400_BAD_REQUEST,
        )

    try:
        delete_observation_command(user, observation_id)
    except (ValueError, PermissionError, BadRequest) as error:
        match type(error):
            case builtins.PermissionError:
                error_status = HTTP_403_FORBIDDEN
            case _:
                error_status = HTTP_400_BAD_REQUEST
        return Response(
            {"error": str(error)},
            status=error_status
        )

    return Response(status=status.HTTP_202_ACCEPTED)
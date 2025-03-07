import logging

from django.core.exceptions import FieldDoesNotExist, BadRequest
from django.db.models import ManyToManyField
from django.http import QueryDict
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from observation_data import observation_management
from observation_data.models import (
    ObservationType,
    AbstractObservation,
    ObservationStatus,
)
from accounts.models import ObservatoryUser, UserPermission
from observation_data.serializers import get_serializer

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

    if isinstance(request_data.get("name", ""), str):
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


@require_POST
@api_view(["POST"])
def edit_observation(request, observation_id):
    """
    Edit an observation which is identified by the observation id.
    The passed data must satisfy the is_valid() method of the corresponding serializer and include all necessary fields.
    Note that the one editing the observation must have the permission to edit all observations or the observation request must be owned by the user.
    :param request: HTTP request with observation data
    :param observation_id: The id of the observation to be edited
    :return: HTTP response with the created observation data or error message
    """

    user = request.user
    observation, response = _fetch_observation(user, observation_id)
    if response:
        return response

    if observation.project_status != ObservationStatus.PENDING:
        return Response(
            {"error": "Only pending observations can be edited"},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Either the observation request is owned by the user or the user is allowed to edit all observations
    can_edit = observation.user.id == user.id or user.has_perm(
        UserPermission.CAN_EDIT_ALL_OBSERVATIONS
    )
    if not can_edit:
        return Response(
            {"error": "Permission denied"},
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

    request_data["user"] = request.user.id

    if isinstance(request_data.get("name", ""), str):
        request_data = _nest_observation_request(
            request_data,
            {
                "ra": "target.ra",
                "dec": "target.dec",
                "name": "target.name",
                "catalog_id": "target.catalog_id",
            },
        )

    serializer = serializer_class(observation, data=request_data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@require_POST
@api_view(["POST"])
def finish_observation(request, observation_id):
    user = request.user
    observation, response = _fetch_observation(user, observation_id)
    if response:
        return response
    can_finish = (
        user.has_perm(UserPermission.CAN_EDIT_ALL_OBSERVATIONS)
        or user == observation.user
    )
    if not can_finish:
        return Response(
            {"error": "Permission denied"},
            status=status.HTTP_403_FORBIDDEN,
        )

    if observation.project_status == ObservationStatus.UPLOADED:
        observation.project_status = ObservationStatus.PENDING_COMPLETION
    else:
        observation.project_status = ObservationStatus.COMPLETED
    observation.save()
    return Response(status=status.HTTP_202_ACCEPTED)


@require_POST
@api_view(["POST"])
def toggle_pause_observation(request, observation_id):
    """
    Pauses the observation with the passed id, or sets the status to Pending.
    User must be the owner of the observation or admin to pause the observation.
    :param request: HTTP request with observation data
    :param observation_id: The id of the observation to be paused
    :return: HTTP response success or error with error message
    """
    user = request.user
    obs, response = _fetch_observation(user, observation_id)
    if response:
        return response

    if not user == obs.user and not user.has_perm(
        UserPermission.CAN_EDIT_ALL_OBSERVATIONS
    ):
        logger.info(
            f"User {user.get_username()} does not have permission to pause observation {observation_id}."
        )
        return Response(
            {
                f"User {user.get_username()} does not have permission to pause observation {observation_id}."
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if obs.project_status == ObservationStatus.PAUSED:
        obs.project_status = ObservationStatus.PENDING
    else:
        obs.project_status = ObservationStatus.PAUSED
    obs.save()

    return Response(status=status.HTTP_202_ACCEPTED)


@require_POST
@api_view(["POST"])
def delete_observation(request, observation_id):
    """
    Deletes the observation with the passed id.
    User must be the owner of the observation or admin to delete the observation.
    :param request: HTTP request with observation data
    :param observation_id: The id of the observation to be deleted
    :return: HTTP response success or error with error message
    """
    user = request.user
    obs, response = _fetch_observation(user, observation_id)
    if response:
        return response

    if not user == obs.user and not user.has_perm(
        UserPermission.CAN_DELETE_ALL_OBSERVATIONS
    ):
        logger.info(
            f"User {user.get_username()} does not have permission to delete observation {observation_id}."
        )
        return Response(
            {
                f"User {user.get_username()} does not have permission to delete observation {observation_id}."
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        observation_management.delete_observation(observation_id)
    except BadRequest as e:
        response = f"Tried to delete observation {observation_id} but status is already set to {ObservationStatus.PENDING_DELETION}. Got {str(e)}"
        return Response({response}, status=status.HTTP_400_BAD_REQUEST)

    return Response(status=status.HTTP_202_ACCEPTED)


def _fetch_observation(user, observation_id) -> (AbstractObservation, Response):
    if not isinstance(user, ObservatoryUser):
        return None, Response(
            {"error": "Invalid user model"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not isinstance(observation_id, int):
        return None, Response(
            {"error": "Invalid observation id"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        obs = AbstractObservation.objects.get(id=observation_id)
    except AbstractObservation.DoesNotExist:
        return None, Response(
            {"error": f"Observation {observation_id} not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    return obs, None


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

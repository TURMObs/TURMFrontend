import logging

from django.contrib.auth.base_user import AbstractBaseUser
from django.forms.models import model_to_dict
from nc_py_api import NextcloudException

import nextcloud.nextcloud_manager as nm
from observation_data.models import AbstractObservation, ObservationStatus

logger = logging.getLogger(__name__)


def delete_user(user: AbstractBaseUser):
    """
    Deletes all data associated with a user. This includes all observation requests and uploaded files.
    :param user: The user to delete
    """
    observation_requests = AbstractObservation.objects.filter(user=user.id)
    for request in observation_requests:
        status = request.project_status
        if status != ObservationStatus.PENDING:
            nc_path = nm.get_observation_file(request)
            if not nc_path:
                continue
            if not nm.file_exists(nc_path):
                continue
            try:
                nm.delete(nc_path)
            except NextcloudException as e:
                logger.error(
                    f"Failed to delete observation {request.id} at {nc_path} for {user}: {e}"
                )
        request.delete()

    user.delete()


def get_all_data(user: AbstractBaseUser):
    """
    Get all data associated with a user. This includes all observation requests.
    :param user: The user to get the data from
    :return: A dictionary containing all associated data
    """
    data = {}
    # Convert the Polymorphic QuerySet into a list of dictionaries
    observation_requests = AbstractObservation.objects.filter(user=user.id)
    data["observation_requests"] = [
        serialize_to_string_rep(request) for request in observation_requests
    ]

    data["user"] = model_to_dict(user)
    data["user"]["password"] = "PASSWORD HASH"
    empty_fields = []
    for key, value in data["user"].items():
        if value is None or value == "" or value == []:
            empty_fields.append(key)
    for field in empty_fields:
        data["user"].pop(field)

    return data


def serialize_to_string_rep(instance):
    """
    Serialize a model instance to a dict but represent nested models as strings.
    """
    serialized_data = model_to_dict(instance)
    for key, value in serialized_data.items():
        if hasattr(value, "__str__"):
            serialized_data[key] = str(value)
    return serialized_data

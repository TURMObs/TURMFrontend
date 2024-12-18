import logging

from django.contrib.auth.models import User
from django.forms.models import model_to_dict
from nc_py_api import NextcloudException

from nextcloud.nextcloud_sync import get_nextcloud_path
import nextcloud.nextcloud_manager as nm
from observation_data.models import AbstractObservation

logger = logging.getLogger(__name__)
def delete_user(user: User):
    """
    Deletes all data associated with a user. This includes all observation requests and uploaded files.
    :param user: The user to delete
    """
    observation_requests = AbstractObservation.objects.filter(user=user.id)
    for request in observation_requests:
        status = request.project_status
        if status == AbstractObservation.ObservationStatus.PENDING:
            request.delete()
        else:
            nc_path = get_nextcloud_path(request)
            try:
                nm.delete(nc_path)
                request.delete()
            except NextcloudException as e:
                logger.error(f"Failed to delete observation {request.id} at {nc_path}: {e}")

    user.delete()


def get_all_data(user: User):
    """
    Get all data associated with a user. This includes all observation requests.
    :param user: The user to get the data from
    :return: A dictionary containing all associated data
    """
    data = {}
    # Convert the Polymorphic QuerySet into a list of dictionaries
    observation_requests = AbstractObservation.objects.filter(user=user.id)
    data["observation_requests"] = [model_to_dict(request) for request in observation_requests]

    data["user"] = model_to_dict(user)

    return data

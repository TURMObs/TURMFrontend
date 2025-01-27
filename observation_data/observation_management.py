import logging

from django.core.exceptions import BadRequest
from nc_py_api import NextcloudException

from accounts.models import ObservatoryUser, UserPermission
from nextcloud.nextcloud_manager import (
    generate_observation_path,
)
from observation_data.models import AbstractObservation, ObservationStatus

import nextcloud.nextcloud_manager as nm

logger = logging.getLogger(__name__)


def delete_observation(user: ObservatoryUser, observation_id: int):
    """
    This function can be used to delete an observation from the database (and if existent from the nextcloud).

    :param user: The user who tries to delete the observation.
    :param observation_id: The id of the observation.
    :raises ValueError: If no such observation exists.
    :raises PermissionError: If the user does not have permission to delete the observation.
    :raises BadRequest: If the observation is already marked for deletion.
    """

    try:
        obs = AbstractObservation.objects.get(id=observation_id)
    except AbstractObservation.DoesNotExist:
        raise ValueError(f"Could not find observation with id {observation_id}")

    if not user == obs.user and not user.has_perm(
        UserPermission.CAN_DELETE_ALL_OBSERVATIONS
    ):
        logger.info(
            f"User {user.get_username()} does not have permission to delete observation {observation_id}."
        )
        raise PermissionError(
            f"User {user.get_username()} does not have permission to delete observation {observation_id}."
        )

    if obs.project_status == ObservationStatus.PENDING_DELETION:
        raise BadRequest(f"Observation {obs.id} is already marked for deletion.")

    if (
        obs.project_status == ObservationStatus.UPLOADED
        or obs.project_status == ObservationStatus.ERROR
    ):  # to prevent mix-up during NINA-Scheduling these observations are deleted in the morning
        obs.project_status = ObservationStatus.PENDING_DELETION
        logger.info(f"Status of observation {obs.id} set to {obs.project_status}")
        obs.save()
        return

    obs.delete()
    logger.info(f"Observation {obs.id} deleted successfully from database.")


def process_pending_deletion():
    """
    Deletes all observations with status PENDING_DELETE from database and if existent from nextcloud.
    Also deletes all users with status
    """
    try:
        nm.initialize_connection()
    except NextcloudException:
        logger.error(
            "Could not connect to Nextcloud. Observations with status PENDING_DELETE were not deleted"
        )
        return

    for obs in AbstractObservation.objects.filter(
        project_status=ObservationStatus.PENDING_DELETION
    ):
        nc_path = generate_observation_path(obs)
        if nm.file_exists(nc_path):
            nm.delete(nc_path)
            logger.info(f"Observation {obs.id} deleted successfully from Nextcloud.")
        else:
            logger.info(f"Observation {obs.id} does not exist in Nextcloud.")

        obs.delete()
        logger.info(f"Observation {obs.id} deleted successfully from database.")
    logger.info("All observations with status PENDING_DELETE deleted successfully.")

    for user in ObservatoryUser.objects.filter(deletion_pending=True):
        user.delete()

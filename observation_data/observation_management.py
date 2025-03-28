import logging

from django.core.exceptions import BadRequest
from django.db.models import Q
from nc_py_api import NextcloudException

from accounts.models import ObservatoryUser
from nextcloud.nextcloud_manager import (
    generate_observation_path,
)
from observation_data.models import AbstractObservation, ObservationStatus

import nextcloud.nextcloud_manager as nm

logger = logging.getLogger(__name__)


def delete_observation(observation_id: int):
    """
    This function can be used to delete an observation from the database (and if existent from the nextcloud).

    :param observation_id: The id of the observation.
    :raises BadRequest: If the observation is already marked for deletion.
    """

    obs = AbstractObservation.objects.get(id=observation_id)

    if obs.project_status == ObservationStatus.PENDING_DELETION:
        raise BadRequest(
            f"Observation {obs.id} with target {obs.target.name} is already marked for deletion."
        )

    if (
        obs.project_status == ObservationStatus.UPLOADED
        or obs.project_status == ObservationStatus.ERROR
    ):  # to prevent mix-up during NINA-Scheduling these observations are deleted in the morning
        obs.project_status = ObservationStatus.PENDING_DELETION
        logger.info(
            f"Status of observation {obs.id} with target {obs.target.name} set to {obs.project_status}"
        )
        obs.save()
        return

    obs.delete()
    logger.info(
        f"Observation {obs.id} with target {obs.target.name} deleted successfully from database."
    )


def process_pending_deletion():
    process_pending_deletion_observations()
    process_pending_deletion_users()


def process_pending_deletion_observations():
    """
    Deletes all observations with status PENDING_DELETE from database and if existent from nextcloud.
    """
    try:
        nm.initialize_connection()
    except NextcloudException:
        logger.error(
            "Could not connect to Nextcloud. Observations with status PENDING_DELETE were not deleted"
        )
        return

    for obs in AbstractObservation.objects.filter(
        Q(project_status=ObservationStatus.PENDING_DELETION)
        | Q(project_status=ObservationStatus.PENDING_COMPLETION)
    ):
        nc_path = generate_observation_path(obs)
        if nm.file_exists(nc_path):
            nm.delete(nc_path)
            logger.info(
                f"Observation {obs.id} with target {obs.target.name} deleted successfully from Nextcloud."
            )
        else:
            logger.info(
                f"Observation {obs.id} with target {obs.target.name} does not exist in Nextcloud."
            )

        if obs.project_status == ObservationStatus.PENDING_COMPLETION:
            obs.project_status = ObservationStatus.COMPLETED
            logger.info(
                f"Status of observation {obs.id} with target {obs.target.name} set to {obs.project_status}"
            )
            obs.save()
        else:
            obs.delete()
            logger.info(
                f"Observation {obs.id} with target {obs.target.name} deleted successfully from database."
            )
    logger.info("All observations with status PENDING_DELETE deleted successfully.")


def process_pending_deletion_users():
    """
    Also deletes all users with status deletion_pending=True
    """
    users = ObservatoryUser.objects.filter(deletion_pending=True)
    for user in users:
        logger.info(f"Deleted user {user.username}")
        user.delete()

    logger.info(f"Deleted {len(users)} users with status deletion_pending.")

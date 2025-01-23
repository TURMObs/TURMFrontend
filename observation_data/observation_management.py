import logging

from django.core.exceptions import BadRequest
from nc_py_api import NextcloudException

from accounts.models import ObservatoryUser, UserPermission
from nextcloud.nextcloud_manager import (
    generate_observation_path,
    initialize_connection,
    file_exists,
    delete,
)
from observation_data.models import AbstractObservation, ObservationStatus

logger = logging.getLogger(__name__)


def delete_observation(user: ObservatoryUser, observation_id: int):
    """
    This function can be used to delete an observation from the database (and if existent from the nextcloud).

    :param user: The user who tries to delete the observation.
    :param observation_id: The id of the observation.
    """

    if obs := AbstractObservation.objects.get(id=observation_id) is None:
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

    if obs.project_status == ObservationStatus.UPLOADED:
        raise BadRequest(
            f"Observation {observation_id} cannot be deleted as this may interfer with NINA scheduling"
        )

    try:
        initialize_connection()
    except NextcloudException as e:
        logger.warning(
            f"Could not connect to Nextcloud. Cannot check if observation is uploaded. Got {e}"
        )
    else:
        nc_path = generate_observation_path(obs)
        if file_exists(nc_path):
            delete(nc_path)
            logger.info(f"Observation {obs.id} deleted successfully from Nextcloud.")
        else:
            logger.info(f"Observation {observation_id} does not exist in Nextcloud.")

    obs.delete()
    logger.info(f"Observation {obs.id} deleted successfully from database.")

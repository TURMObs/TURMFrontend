from itertools import chain
from django.utils import timezone
from nc_py_api import NextcloudException

from observation_data.models import (
    AbstractObservation,
    ScheduledObservation,
    ObservationStatus,
)
from observation_data.serializers import get_serializer
import logging
import nextcloud.nextcloud_manager as nm

"""
This module retrieves the observation requests for a night and uses the nextcloud_manager to upload them to the nextcloud.
Method upload_observation is supposed to be triggered using a cron-Job
"""

logger = logging.getLogger(__name__)


def calc_progress(observation: dict) -> float:
    """
    Calculates the progress of the observation.
    An observation can contain multiple filters and therefore multiple required/accepted_amounts.

    :param observation: Observation as dict. Per definition contains at least one filter
    :return fraction of progress of observation
    """
    filters = observation["targets"][0]["exposures"]

    required_amount = 0
    accepted_amount = 0

    for f in filters:
        required_amount += f["requiredAmount"]
        accepted_amount += f["acceptedAmount"]

    return round(accepted_amount / required_amount, 2)


def upload_observations(today=timezone.now()):
    """
    Uploads all observations with project_status "upload_pending" from the database to the nextcloud and updates the status accordingly.

    :params today: datetime; default=timezone.now(). Can be changed for debugging purposes.
    """

    # Handling of observations, that can be uploaded anytime (all non-scheduled observations)
    pending_observations = AbstractObservation.objects.filter(
        project_status=ObservationStatus.PENDING
    ).not_instance_of(ScheduledObservation)

    # Handling of Scheduled Observation. If Observation is due today, it is included in pending_observation
    scheduled_observations = (
        AbstractObservation.objects.instance_of(ScheduledObservation)
        .exclude(
            project_status=ObservationStatus.COMPLETED,
        )
        .exclude(project_status=ObservationStatus.ERROR)
    )
    local_day = timezone.localdate(today)
    for obs in scheduled_observations:
        if (timezone.localdate(obs.start_scheduling) > local_day) or timezone.localdate(
            obs.end_scheduling
        ) < local_day:
            continue
        if local_day != timezone.localdate(obs.next_upload):
            continue
        pending_observations = chain(pending_observations, [obs])

    # upload all pending_observation to Nextcloud.
    list_to_upload = list(pending_observations)
    logger.info(f"Uploading {len(list_to_upload)} observations ...")
    try:
        nm.initialize_connection()
    except NextcloudException as e:
        logger.error(f"Failed to initialize connection: {e}")

    for obs in list_to_upload:
        serializer_class = get_serializer(obs.observation_type)
        serializer = serializer_class(obs)

        obs_dict = serializer.data
        nc_path = nm.generate_observation_path(obs)
        try:
            nm.upload_dict(nc_path, obs_dict)
            obs.project_status = ObservationStatus.UPLOADED
            logger.info(
                f"Uploaded observation {obs_dict['name']} with id {obs.id} to {nc_path}"
            )

        except NextcloudException as e:
            logger.error(
                f"Failed to upload observation {obs_dict['name']} with id {obs.id}: {e}"
            )
        obs.save()

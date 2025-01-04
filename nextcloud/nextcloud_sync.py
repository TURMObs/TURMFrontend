import math
from datetime import timedelta
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


def check_for_progress(obs: AbstractObservation, nc_dict: dict) -> bool:
    """
    Checks whether pictures of the corresponding observation have been taken compared to the current status in the database.

    :param obs: the observation from the database
    :param nc_dict: the dict of the observation in the nextcloud.
    :return True if the progress of the both params do NOT match. False otherwise.
    """

    serializer_class = get_serializer(obs.observation_type)
    serializer = serializer_class(obs)
    obs_dict = serializer.data

    nc_progress = nc_dict["targets"][0]["exposures"]
    db_progress = obs_dict["targets"][0]["exposures"]

    for e_nc, db_progression in zip(nc_progress, db_progress):
        if e_nc["acceptedAmount"] != db_progression["acceptedAmount"]:
            return True
    return False


def calc_progress(observation: dict) -> float:
    """
    Calculates the progress of the observation.
    An observation can contain multiple filters and therefore multiple required/accepted_amounts.

    :param observation: Observation as dict. Per definition contains at least one filter
    :return progress as decimal (100.0 = Done)
    """
    filters = observation["targets"][0]["exposures"]

    required_amount = 0
    accepted_amount = 0

    for f in filters:
        required_amount += f["requiredAmount"]
        accepted_amount += f["acceptedAmount"]

    return round((accepted_amount / required_amount) * 100, 2)

def download_observations(today=timezone.now()):
    """
    Downloads all observations from the nextcloud, checks for progress and updates database accordingly.

    :params today: datetime; default=timezone.now(). Can be changed for debugging purposes.
    """

    observations = AbstractObservation.objects.filter(project_status=ObservationStatus.UPLOADED)
    nm.initialize_connection()
    for obs in observations:
        try:
            nc_path = nm.get_observation_file(obs)
            nc_dict = nm.download_dict(nc_path)
        except NextcloudException as e:
            logger.error(
                f"Expected observation {obs.id} to be uploaded in nextcloud to retrieve progress, but got: {e}"
            )
            obs.project_status = ObservationStatus.ERROR
            obs.save()
            continue

        # if there has been no progress, there only needs to be a check whether the scheduled observations are outdated
        if not check_for_progress(obs, nc_dict):
            if isinstance(obs, ScheduledObservation) and obs.end_scheduling < timezone.localdate(today): # maybe <=
                # although the observation is not finished, its reached its end of scheduling and is therefore removed.
                nm.delete(nc_path)
                obs.project_status = ObservationStatus.COMPLETED
                obs.save()
            continue # no pictures have been taken

        # updating non-scheduled observation in db
        if not isinstance(obs, ScheduledObservation):
            progress = calc_progress(nc_dict)
            if progress > obs.project_completion:
                obs.project_completion = progress
            if progress == 100.0:
                obs.project_status = ObservationStatus.COMPLETED
                try:
                    nm.delete(nc_path)
                except NextcloudException as e:
                    logger.error(
                        f"Tried to delete observation {obs.id} because progress is 1, but got: {e}"
                    )
        # updating scheduled observation in db
        else:
            partial_progress = calc_progress(nc_dict)
            new_upload = obs.next_upload + timedelta(days=obs.cadance)

            if partial_progress != 0.0 and new_upload <= obs.end_scheduling and timezone.localdate(today) >= obs.next_upload:
                # following conditions must be met to schedule a new upload:
                # - there has been progress
                # - the new upload is before the end of scheduling
                # - there isn't already an upload scheduled in the future
                obs.next_upload = new_upload

            if timezone.localdate(today) > obs.end_scheduling:
                obs.project_status = ObservationStatus.COMPLETED
                try:
                    nm.delete(nc_path)
                except NextcloudException as e:
                    logger.error(
                        f"Tried to delete observation {obs.id} because its exceeded its scheduled end, but got: {e}"
                    )
            elif partial_progress == 100.0:
                try:
                    nm.delete(nc_path)
                except NextcloudException as e:
                    obs.project_status = ObservationStatus.ERROR
                    logger.error(
                        f"Tried to delete observation {obs.id} because partial progress is 1, but got: {e}"
                    )

            # todo calc progress in db
            duration = obs.end_scheduling - obs.start_scheduling
            obs.project_completion = (timezone.localdate(today) / duration) * 100

        obs.save()

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
            obs.project_status = ObservationStatus.ERROR
        obs.save()

import datetime
from datetime import timedelta
from itertools import chain

from django.db.models import Q
from django.utils import timezone
from nc_py_api import NextcloudException

from nextcloud.nextcloud_manager import generate_observation_path
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
`upload_observation()` and `update_observation()` are supposed to be triggered via a cron-Job
"""

logger = logging.getLogger(__name__)


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


def get_data_from_nc(obs: AbstractObservation):
    """
    Downloads the dict of the observation from the nextcloud.
    If an error occurs, it will be logged and the status set to error.
    Requires nextcloud connection to be initialized.

    :param obs: Observation to retrieve the dict from.

    :return: the dictionary of the observation and the nc_path. The progress is None if an error occurs.
    """
    try:
        nc_path = nm.get_observation_file(obs)

        if nc_path is None:
            logger.error(
                f"Expected observation {obs.id} to be uploaded in nextcloud to retrieve progress, but got could not find it under expected path: {generate_observation_path(obs)}"
            )
            return None, None

        nc_dict = nm.download_dict(nc_path)
    except NextcloudException as e:
        logger.error(
            f"Expected observation {obs.id} to be uploaded in nextcloud to retrieve progress, but got: {e}"
        )
        return None, None

    return calc_progress(nc_dict), nc_path


def update_non_scheduled_observations():
    """
    Downloads all non-scheduled observations from the nextcloud, checks for progress and updates database accordingly.
    """

    observations = AbstractObservation.objects.filter(
        project_status=ObservationStatus.UPLOADED
    ).not_instance_of(ScheduledObservation)

    try:
        nm.initialize_connection()
    except NextcloudException as e:
        logger.error(f"Failed to initialize connection: {e}")
        return

    logger.info(
        f"Got {len(observations)} non-scheduled observations to check for updates."
    )

    for obs in observations:
        progress, nc_path = get_data_from_nc(obs)
        if (
            progress is None or nc_path is None
        ):  # an error occurred and has already been logged
            obs.project_status = ObservationStatus.ERROR
            obs.save()
            continue
        if progress != obs.project_completion:
            obs.project_completion = progress
        if progress == 100.0:
            obs.project_status = ObservationStatus.COMPLETED
            try:
                nm.delete(nc_path)
                logger.info(
                    f"Deleted observation {obs.id} from nextcloud as it is completed. Set status to {ObservationStatus.COMPLETED}!"
                )
            except NextcloudException as e:
                logger.error(
                    f"Tried to delete observation {obs.id} because progress is 100, but got: {e}"
                )
                obs.project_status = ObservationStatus.ERROR
                obs.save()
        obs.save()


def update_scheduled_observations(today: datetime = timezone.now()):
    """
    Downloads all scheduled observations from the nextcloud, checks for progress and updates database accordingly.

    :param today: datetime; default=timezone.now(). Can be changed for debugging purposes.

    """
    observations = AbstractObservation.objects.instance_of(ScheduledObservation).filter(
        Q(project_status=ObservationStatus.PENDING)
        | Q(project_status=ObservationStatus.UPLOADED)
    )

    try:
        nm.initialize_connection()
    except NextcloudException as e:
        logger.error(f"Failed to initialize connection: {e}")
        return

    logger.info(f"Got {len(observations)} scheduled observations to check for updates.")

    for obs in observations:
        # Calculates the progress of a scheduled observation. Only considers the continuance of the days, not whether pictures were actually taken.
        duration = (obs.end_scheduling - obs.start_scheduling).days
        if duration <= 0:
            obs.project_completion = 100.0
        else:
            elapsed_time = (today - obs.start_scheduling).days
            obs.project_completion = round(
                max(0.0, min((elapsed_time / duration) * 100, 100.0)), 2
            )

        if obs.project_status == ObservationStatus.PENDING:
            # If the status is pending, the observation currently waits for the next upload during its scheduling and the prior partial observation is finished.
            # No further actions required.
            obs.save()
            continue

        partial_progress, nc_path = get_data_from_nc(obs)
        if partial_progress is None:  # has already been logged
            obs.project_status = ObservationStatus.ERROR
            obs.save()
            continue

        new_upload = today + timedelta(days=obs.cadence - 1)

        if (
            partial_progress != 0.0
            and timezone.localdate(new_upload) <= timezone.localdate(obs.end_scheduling)
            and timezone.localdate(today) >= timezone.localdate(obs.next_upload)
        ):
            # Following conditions must be met to schedule a new upload:
            # - there has been progress for the first time
            # - the new upload is before the end of scheduling
            # - there isn't already an upload scheduled in the future
            obs.next_upload = new_upload

        if obs.project_completion == 100.0:
            # If an observation has reached 100.0% project_completion (i.e. the time windows has passed), it is considered done regardless the actual pictures taken.
            try:
                obs.project_status = ObservationStatus.COMPLETED
                nm.delete(nc_path)
                logger.info(
                    f"Deleted observation {obs.id} from nextcloud as it is completed. Set status to {ObservationStatus.COMPLETED}."
                )
            except NextcloudException as e:
                logger.error(
                    f"Tried to delete observation {obs.id} because it has reached its scheduled end, but got: {e}"
                )
                obs.project_status = ObservationStatus.ERROR
                obs.save()
        elif partial_progress == 100.0:
            # If an observation has reached 100.0% partial completion, it is deleted from the nextcloud since no images have to be taken until it is uploaded again
            try:
                obs.project_status = ObservationStatus.PENDING  # set status to pending to indicate observation currently does NOT exist in the nextcloud.
                nm.delete(nc_path)
                logger.info(
                    f"Deleted observation {obs.id} from nextcloud as it is partially completed. Set status to {ObservationStatus.PENDING} to prepare for new upload on {obs.next_upload}."
                )
            except NextcloudException as e:
                logger.error(
                    f"Tried to delete observation {obs.id} because partial progress is 100, but got: {e}"
                )
                obs.project_status = ObservationStatus.ERROR
                obs.save()

        obs.save()


def update_observations(today: datetime = timezone.now()):
    """
    Wrapper method for calling 'download_non_scheduled_observations' and 'download_scheduled_observations'.

    :param today: datetime; default=timezone.now(). Can be changed for debugging purposes.
    """
    update_non_scheduled_observations()
    update_scheduled_observations(today)


def upload_observations(today=timezone.now()):
    """
    Uploads all observations with project_status "upload_pending" from the database to the nextcloud and updates the status accordingly.

    :param today: datetime; default=timezone.now(). Can be changed for debugging purposes.
    """

    # Handling of observations, that can be uploaded anytime (all non-scheduled observations)
    pending_observations = AbstractObservation.objects.filter(
        project_status=ObservationStatus.PENDING
    ).not_instance_of(ScheduledObservation)

    # Handling of Scheduled Observation. If Observation is due today, it is included in pending_observation
    scheduled_observations = AbstractObservation.objects.instance_of(
        ScheduledObservation
    ).filter(
        Q(project_status=ObservationStatus.PENDING)
        | Q(project_status=ObservationStatus.UPLOADED)
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

    # Upload all pending_observation to Nextcloud.
    list_to_upload = list(pending_observations)
    logger.info(f"Uploading {len(list_to_upload)} observations ...")

    try:
        nm.initialize_connection()
    except NextcloudException as e:
        logger.error(f"Failed to initialize connection: {e}")
        return

    for obs in list_to_upload:
        serializer_class = get_serializer(obs.observation_type)
        serializer = serializer_class(obs)

        obs_dict = serializer.data
        nc_path = nm.generate_observation_path(obs)
        try:
            nm.upload_dict(nc_path, obs_dict)
            logger.info(
                f"Uploaded observation {obs_dict['name']} with id {obs.id} to {nc_path}"
            )
            obs.project_status = ObservationStatus.UPLOADED

        except NextcloudException as e:
            logger.error(
                f"Failed to upload observation {obs_dict['name']} with id {obs.id}: {e}"
            )
            obs.project_status = ObservationStatus.ERROR
        obs.save()

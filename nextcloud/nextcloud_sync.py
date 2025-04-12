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
    ObservationType,
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
                f"Expected observation {obs.id} with target {obs.target.name} to be uploaded in nextcloud to retrieve progress, but could not find it under expected path: {generate_observation_path(obs)}"
            )
            return None, None

        nc_dict = nm.download_dict(nc_path)
    except NextcloudException as e:
        logger.error(
            f"Expected observation {obs.id} with target {obs.target.name} to be uploaded in nextcloud to retrieve progress, but got: {e}"
        )
        return None, None

    return calc_progress(nc_dict), nc_path


def update_non_scheduled_observations(today: datetime.date = timezone.now().date()):
    """
    Downloads all non-scheduled observations from the nextcloud, checks for progress and updates database accordingly.
    """
    try:
        nm.initialize_connection()
    except NextcloudException as e:
        logger.error(f"Failed to initialize connection: {e}")
        return

    observations = AbstractObservation.objects.filter(
        project_status__in=[ObservationStatus.UPLOADED, ObservationStatus.PAUSED]
    )

    excluded_observations = []
    for obs in observations:
        if isinstance(obs, ScheduledObservation) and obs.start_scheduling:
            excluded_observations.append(obs)
        if obs.project_status == ObservationStatus.PAUSED and not nm.file_exists(
            nm.generate_observation_path(obs)
        ):
            excluded_observations.append(obs)

    observations = observations.exclude(
        id__in=[obs.id for obs in excluded_observations]
    )  # exclude all scheduled observations, as well as all observations that are not in the nextcloud

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
                    f"Deleted observation {obs.id} with target {obs.target.name} from nextcloud as it is completed. Set status to {ObservationStatus.COMPLETED}!"
                )
            except NextcloudException as e:
                logger.error(
                    f"Tried to delete observation {obs.id} with target {obs.target.name} because progress is 100, but got: {e}"
                )
                obs.project_status = ObservationStatus.ERROR
                obs.save()
        if "start_observation" in obs.__dict__ and "end_observation" in obs.__dict__:
            if not (obs.start_observation and obs.end_observation):
                continue

            if obs.end_observation < timezone.make_aware(
                datetime.datetime.combine(today, timezone.now().time())
            ):
                if progress == 0.0:
                    obs.project_status = ObservationStatus.FAILED
                else:
                    obs.project_status = ObservationStatus.COMPLETED
                try:
                    nm.delete(nc_path)
                    logger.info(
                        f"Deleted observation {obs.id} with target {obs.target.name} from nextcloud as it is completed. Set status to {ObservationStatus.COMPLETED}!"
                    )
                except NextcloudException as e:
                    logger.error(
                        f"Tried to delete observation {obs.id} with target {obs.target.name} because progress is 100, but got: {e}"
                    )
                    obs.project_status = ObservationStatus.ERROR
                    obs.save()
        obs.save()


def update_scheduled_observations(today: datetime.date = timezone.now().date()):
    """
    Downloads all scheduled observations from the nextcloud, checks for progress and updates database accordingly.

    :param today: datetime.date; default=timezone.now().date(). Can be changed for debugging purposes.
    """
    try:
        nm.initialize_connection()
    except NextcloudException as e:
        logger.error(f"Failed to initialize connection: {e}")
        return

    observations = AbstractObservation.objects.instance_of(ScheduledObservation).filter(
        Q(project_status=ObservationStatus.PENDING)
        | Q(project_status=ObservationStatus.UPLOADED)
        | Q(project_status=ObservationStatus.PAUSED)
    )

    excluded_observations = []
    for obs in observations:
        if not obs.start_scheduling:
            excluded_observations.append(obs)
        if obs.project_status == ObservationStatus.PAUSED and not nm.file_exists(
            nm.generate_observation_path(obs)
        ):
            excluded_observations.append(obs)

    observations = observations.exclude(
        id__in=[obs.id for obs in excluded_observations]
    )  # exclude all non-scheduled observations, as well as all observations that are not in the nextcloud

    logger.info(f"Got {len(observations)} scheduled observations to check for updates.")

    for obs in observations:
        # Calculates the progress of a scheduled observation. Only considers the continuance of the days, not whether pictures were actually taken.
        duration = (obs.end_scheduling - obs.start_scheduling).days + 1
        if duration <= 0:
            obs.project_completion = 100.0
        else:
            elapsed_time = (today - obs.start_scheduling).days
            obs.project_completion = round(
                max(0.0, min((elapsed_time / duration) * 100, 100.0)), 2
            )

        if obs.project_completion == 100.0:
            # If an observation has reached 100.0% project_completion (i.e. the time windows has passed), it is considered done regardless the actual pictures taken.
            if obs.project_status == ObservationStatus.UPLOADED:
                try:
                    nm.delete(nm.generate_observation_path(obs))
                    logger.info(
                        f"Deleted observation {obs.id} with target {obs.target.name} from nextcloud as it is completed. Set status to {ObservationStatus.COMPLETED}."
                    )
                except NextcloudException as e:
                    logger.error(
                        f"Tried to delete observation {obs.id} with target {obs.target.name} because it has reached its scheduled end, but got: {e}"
                    )
                    obs.project_status = ObservationStatus.ERROR
                    obs.save()
                    continue
            obs.project_status = ObservationStatus.COMPLETED
            obs.save()
            continue

        if (
            obs.project_status == ObservationStatus.PENDING
            or obs.project_status == ObservationStatus.PAUSED
        ):
            # If the status is pending or paused, the observation currently waits for the next upload during its scheduling and the prior partial observation is finished.
            # No further actions required.
            obs.save()
            continue

        partial_progress, nc_path = get_data_from_nc(obs)
        if partial_progress is None:  # has already been logged
            obs.project_status = ObservationStatus.ERROR
            obs.save()
            continue

        if "start_observation" in obs.__dict__ and "end_observation" in obs.__dict__:
            if obs.start_observation and obs.end_observation:
                if obs.end_observation < timezone.make_aware(
                    datetime.datetime.combine(today, timezone.now().time())
                ):
                    partial_progress = 100.0

        new_upload = today + timedelta(days=obs.cadence - 1)

        if (
            partial_progress != 0.0
            and new_upload <= obs.end_scheduling
            and today >= obs.next_upload
        ):
            # Following conditions must be met to schedule a new upload:
            # - there has been progress for the first time
            # - the new upload is before the end of scheduling
            # - there isn't already an upload scheduled in the future
            obs.next_upload = new_upload

        if (
            partial_progress != 100.0
            and obs.observation_type == ObservationType.EXPERT
            and obs.start_observation_time
            and obs.project_status == ObservationStatus.UPLOADED
            and today >= obs.next_upload
        ):
            # Checking uploaded expert observations, even if their partial progress is not 100.0%. If the observation time has passed, the observation is considered done.
            try:
                nm_dict = nm.download_dict(nc_path)
            except NextcloudException as e:
                logger.error(
                    f"Failed to download observation {obs.id} with target {obs.target.name} because progress is 0, but got: {e}"
                )
                obs.project_status = ObservationStatus.ERROR
                obs.save()
                continue
            target_date = timezone.make_aware(
                datetime.datetime.strptime(
                    nm_dict["targets"][0]["endDateTime"], "%Y-%m-%d %H:%M:%S"
                ),
                timezone.get_current_timezone(),
            )
            date_now = timezone.make_aware(
                datetime.datetime.combine(today, timezone.now().time()),
                timezone.get_current_timezone(),
            )
            if target_date <= date_now:
                # Further progress is impossible, since the observation time has already passed.
                partial_progress = 100.0
                if new_upload < obs.end_scheduling:
                    obs.next_upload = new_upload

        if partial_progress == 100.0:
            # If an observation has reached 100.0% partial completion, it is deleted from the nextcloud since no images have to be taken until it is uploaded again
            try:
                obs.project_status = ObservationStatus.PENDING  # set status to pending to indicate observation currently does NOT exist in the nextcloud.
                nm.delete(nc_path)
                logger.info(
                    f"Deleted observation {obs.id} with target {obs.target.name} from nextcloud as it is partially completed. Set status to {ObservationStatus.PENDING} to prepare for new upload on {obs.next_upload}."
                )
            except NextcloudException as e:
                logger.error(
                    f"Tried to delete observation {obs.id} with target {obs.target.name} because partial progress is 100, but got: {e}"
                )
                obs.project_status = ObservationStatus.ERROR
            obs.save()

        obs.save()


def update_observations(today: datetime.date = timezone.now().date()):
    """
    Wrapper method for calling 'download_non_scheduled_observations' and 'download_scheduled_observations'.

    :param today: datetime; default=timezone.now().date. Can be changed for debugging purposes.
    """
    update_non_scheduled_observations(today)
    update_scheduled_observations(today)


def upload_observations(today: datetime.date = timezone.now().date()):
    """
    Uploads all observations with project_status "upload_pending" from the database to the nextcloud and updates the status accordingly.

    :param today: datetime; default=timezone.now(). Can be changed for debugging purposes.
    """
    try:
        nm.initialize_connection()
    except NextcloudException as e:
        logger.error(f"Failed to initialize connection: {e}")
        return

    # Handling of observations, that can be uploaded anytime (all non-scheduled observations)
    pending_observations = AbstractObservation.objects.filter(
        Q(project_status=ObservationStatus.PENDING)
        | Q(project_status=ObservationStatus.UPLOADED)
    )

    scheduled_observations = []
    excluded_observations = []
    for obs in pending_observations:
        if (
            isinstance(obs, ScheduledObservation)
            and obs.start_scheduling
            and (
                obs.project_status == ObservationStatus.PENDING
                or obs.project_status == ObservationStatus.UPLOADED
            )
        ):
            scheduled_observations.append(obs)
        elif obs.project_status == ObservationStatus.UPLOADED:
            excluded_observations.append(obs)

    pending_observations = pending_observations.exclude(
        id__in=[obs.id for obs in scheduled_observations]
    )  # exclude all scheduled observations

    # Handling of Scheduled Observation. If Observation is due today, it is included in pending_observation
    for obs in scheduled_observations:
        if obs.start_scheduling > today or obs.end_scheduling < today:
            continue
        if today < obs.next_upload:
            continue
        pending_observations = chain(pending_observations, [obs])

    # Upload all pending_observation to Nextcloud.
    list_to_upload = list(pending_observations)
    logger.info(f"Uploading {len(list_to_upload)} observations ...")

    for obs in list_to_upload:
        if not obs.observatory:
            obs.project_status = ObservationStatus.ERROR
            logger.warning(f"Observation {obs.id} has no observatory assigned.")
            obs.save()
            continue

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
                f"Failed to upload observation {obs.id} to {nc_path}. Got: {e}"
            )
            obs.project_status = ObservationStatus.ERROR
        obs.save()

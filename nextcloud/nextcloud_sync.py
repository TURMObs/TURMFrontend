from itertools import chain

from django.utils import timezone


from observation_data.models import (
    AbstractObservation,
    ScheduledObservation,
    ObservationStatus,
)
from observation_data.serializers import get_serializer
import os
import django
import nextcloud.nextcloud_manager as nm

"""
This module retrieves the observation requests for a night and uses the nextcloud_manager to upload them to the nextcloud.
It is supposed to run in a cron-Job 
"""

# todo fix this when deployed so the script can run on its own
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TURMFrontend.settings")
django.setup()


def get_nextcloud_path(
    abstract_observation: AbstractObservation, dec_offset: int = 5
) -> str:
    """
    Creates the path of the file according to the scheme "[Observatory]/Projects/[Observation_ID].json". Observation_ID is the unique identifier for all observations.

    :param abstract_observation: Abstract observation. Is instance of subclass of AbstractObservation and contains all necessary information to build the path
    :project_name: Name of the observation project. Needs to be included because it is not possible to extract this from abstract_observation.
    :return path of the file in nextcloud
    """

    # get the name of the project. Inefficient to get serializer again, but prevents necessity of another argument
    project_name = get_serializer(abstract_observation.observation_type)(
        abstract_observation
    ).data["name"]

    observatory_string = str(abstract_observation.observatory.name).upper()
    id = abstract_observation.id
    offset_f = f"{id:0{dec_offset}}"
    s = observatory_string + "/Projects/" + offset_f + "_" + project_name + ".json"
    return s


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

    return accepted_amount / required_amount


"""
def update_database():
    
    Checks which observations have been done and updates the database accordingly.
    First it gets all observation that are not finished yet and gets the corresponding dicts from both the nc and the db.
    Then it calculates the progress from the nc JSON. If it has changed (aka pictures have been taken) it updates the database accordingly.
    If an observation is entirely finished, its status is set accordingly and the JSON is deleted from the nc.
    

    # gets all observations not finished yet
    observations = AbstractObservation.objects.filter(project_completion__lt=100)
    for observation in observations:
        serializer_class = get_serializer(observation.observation_type)
        serializer = serializer_class(observation)

        # downloads the JSON of the observation from the NC and calculates the progress
        nc_path = get_nextcloud_path(observation)
        obs_dict_nc = nm.download_dict(nc_path=nc_path)
        progress_nc = calc_progress(obs_dict_nc)

        if progress_nc != observation.project_completion:
            # schreiben des neuen JSON in DB
            # todo

            # ändern der project_completion
            observation.project_completion = progress_nc

            # falls fertig beobachtet: Status ändern und JSON aus NC löschen
            if observation.project_completion == 100:
                observation.project_status = ObservationStatus.COMPLETED
                nm.delete(nc_path=nc_path)
            observation.save()
"""


def upload_observations(today=timezone.now()):
    """
    Uploads all observations with project_status "upload_pending" from the database to the nextcloud and updates the status accordingly.

    :params today: datetime; default=timezone.now(). Can be changed for debugging purposes.
    """

    # Handling of observations, that can be uploaded anytime (all non scheduled observations)
    pending_observations = AbstractObservation.objects.filter(
        project_status=ObservationStatus.PENDING
    ).not_instance_of(
        ScheduledObservation
    )  # exclude ScheduledObservation. They are handled explicit

    # Handling of Scheduled Observation. If Observation is due today, it is included in pending_observation
    scheduled_observations = (
        AbstractObservation.objects.instance_of(ScheduledObservation)
        .exclude(
            project_status=ObservationStatus.COMPLETED,
        )
        .exclude(project_status=ObservationStatus.ERROR)
    )
    for obs in scheduled_observations:
        if timezone.localdate(obs.start_scheduling) > timezone.localdate(
            today
        ) or timezone.localdate(obs.end_scheduling) < timezone.localdate(today):
            continue
        if (
            timezone.localdate(today) - timezone.localdate(obs.start_scheduling)
        ).days % obs.cadence != 0:
            continue
        pending_observations = chain(pending_observations, [obs])

    # print(pending_observations)
    test_list = list(pending_observations)
    # print("Length of pending_observations: ", len(test_list))

    # upload all pending_observation to Nextcloud.
    nm.initialize_connection()
    for obs in test_list:
        try:
            serializer_class = get_serializer(obs.observation_type)
            serializer = serializer_class(obs)

            obs_dict = serializer.data
            nc_path = get_nextcloud_path(obs)

            nm.upload_dict(nc_path, obs_dict)
            obs.project_status = ObservationStatus.UPLOADED
            # print(f"Uploaded observation to {nc_path}")

        except Exception:
            # todo log as critical error
            print("Failed to upload observation: ", obs.id)
        obs.save()

from nc_py_api import NextcloudException

from observation_data.models import AbstractObservation
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


def build_nextcloud_path(
    abstract_observation: AbstractObservation, project_name: str, dec_offset: int = 5
) -> str:
    """
    Creates the path of the file according to the scheme "[Observatory]/Projects/[Observation_ID].json". Observation_ID is the unique identifier for all observations.

    :param abstract_observation: Abstract observation. Is instance of subclass of AbstractObservation and contains all necessary information to build the path
    :project_name: Name of the observation project. Needs to be included because it is not possible to extract this from abstract_observation.
    :return path of the file in nextcloud
    """
    observatory_string = str(abstract_observation.observatory.name).upper()
    observation_id = abstract_observation.id
    offset_format = "%0" + str(dec_offset) + "d"

    return (
        observatory_string
        + "/Projects/"
        + (offset_format % observation_id)
        + "_"
        + project_name
        + ".json"
    )

def upload_observations():
    """
    Uploads all observations with project_status "upload_pending" from the database to the nextcloud and updates the status accordingly.
    """
    observations = AbstractObservation.objects.filter(
        project_status=AbstractObservation.ObservationStatus.PENDING
    )

    nm.initialize_connection()
    for observation in observations:
        serializer_class = get_serializer(observation.observation_type)
        serializer = serializer_class(observation)

        obs_dict = serializer.data
        nc_path = build_nextcloud_path(observation, obs_dict["name"])

        try:
            nm.upload_dict(nc_path, obs_dict)
            observation.project_status = AbstractObservation.ObservationStatus.UPLOADED
        except NextcloudException:
            observation.project_status = AbstractObservation.ObservationStatus.ERROR
        observation.save()


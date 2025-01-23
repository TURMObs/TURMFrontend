import os

from django.core.management.base import BaseCommand

import logging

from dotenv import load_dotenv

import nextcloud.nextcloud_manager as nm
from accounts.models import ObservatoryUser
from observation_data.models import ImagingObservation
from observation_data.serializers import _create_observation, ImagingObservationSerializer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Creates path in the nextcloud"

    def handle(self, *args, **options):
        obs_name = options["name"]

        data = {'target': {'ra': '10 10 10 ', 'dec': '10 10 10 ', 'name': obs_name, 'catalog_id': 'm42'}, 'observatory': 'TURMX', 'observation_type': 'Imaging', 'filter_set': ['L'], 'exposure_time': '30', 'frames_per_filter': '100', 'user': 1}
        serializer = ImagingObservationSerializer(data=data)

        if not serializer.is_valid():
            print("ihr schwachköpfe")
            return

        serializer.save()

    def add_arguments(self, parser):
        parser.add_argument(
            "name",
            type=str,
            help="The name of the observation you want to create",
        )

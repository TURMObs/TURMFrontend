import os
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

import nextcloud.nextcloud_manager as nm
import logging

from observation_data.models import AbstractObservation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Deletes all observations from the database and wipes the nextcloud"

    def handle(self, *args, **options):
        observations = AbstractObservation.objects.all()

        for obs in observations:
            obs.delete()

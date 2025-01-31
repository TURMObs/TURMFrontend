from django.core.management.base import BaseCommand

import logging

from observation_data import observation_management
from observation_data.models import AbstractObservation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Deletes all observation from the database and the nextcloud. Use with CAUTION as it might interfere with NINA scheduling."

    def handle(self, *args, **options):
        for obs in AbstractObservation.objects.all():
            observation_management.delete_observation(obs)
        observation_management.process_pending_deletion_observations()

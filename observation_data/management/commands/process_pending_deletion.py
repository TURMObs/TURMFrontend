from django.core.management.base import BaseCommand

import logging

from observation_data.observation_management import process_pending_deletion

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Deletes all observations with status PENDING_DELETION and all users with deletion_pending=True"

    def handle(self, *args, **options):
        process_pending_deletion()

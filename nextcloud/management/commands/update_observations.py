from django.core.management.base import BaseCommand
from nextcloud.nextcloud_sync import update_observations
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Downloads observations from Nextcloud and updates database"

    def handle(self, *args, **options):
        try:
            update_observations()
        except Exception as e:
            logger.error(f"Error downloading observations: {e}")
            self.stdout.write(self.style.ERROR(f"Error downloading observations: {e}"))

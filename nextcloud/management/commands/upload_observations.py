from django.core.management.base import BaseCommand
from nextcloud.nextcloud_sync import upload_observations
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Uploads observations from database to Nextcloud"

    def handle(self, *args, **options):
        try:
            upload_observations()
        except Exception as e:
            logger.error(f"Error uploading observations: {e}")
            self.stdout.write(self.style.ERROR(f"Error uploading observations: {e}"))
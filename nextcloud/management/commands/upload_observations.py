from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from nextcloud.nextcloud_sync import upload_observations
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Uploads observations from database to Nextcloud"

    def handle(self, *args, **options):
        try:
            time_delta = 0
            if options["days"]:
                time_delta = options["days"]
            upload_observations(timezone.now() + timedelta(days=time_delta))

        except Exception as e:
            logger.error(f"Error uploading observations: {e}")
            self.stdout.write(self.style.ERROR(f"Error uploading observations: {e}"))

    def add_arguments(self, parser):
        parser.add_argument("--days", "-d", type=int, help="Timedelta of days from now")

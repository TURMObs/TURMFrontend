from datetime import timedelta
from django.utils import timezone

from django.core.management.base import BaseCommand
from nextcloud.nextcloud_sync import update_observations
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Downloads observations from Nextcloud and updates database"

    def handle(self, *args, **options):
        try:
            time_delta = 0
            if options["days"]:
                time_delta = options["days"]
            update_observations(timezone.now() + timedelta(days=time_delta))
        except Exception as e:
            logger.error(f"Error downloading observations: {e}")
            self.stdout.write(self.style.ERROR(f"Error downloading observations: {e}"))

    def add_arguments(self, parser):
        parser.add_argument("--days", "-d", type=int, help="Timedelta of days from now")

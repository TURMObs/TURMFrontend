from datetime import timedelta
from django.utils import timezone

from django.core.management.base import BaseCommand

from nextcloud import nextcloud_manager
from nextcloud.nextcloud_sync import update_observations
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Downloads observations from Nextcloud and updates database"

    def handle(self, *args, **options):
        time_delta = 0
        old_prefix = ""
        if options["days"]:
            time_delta = options["days"]

        if options["prefix"]:
            old_prefix = options["prefix"]
            nextcloud_manager.prefix = options["prefix"].strip("/")

        try:
            update_observations(timezone.now() + timedelta(days=time_delta))
        except Exception as e:
            logger.error(f"Error updating observations: {e}")
            self.stdout.write(self.style.ERROR(f"Error downloading observations: {e}"))

        if options["prefix"]:
            nextcloud_manager.prefix = old_prefix


def add_arguments(self, parser):
    parser.add_argument("--days", "-d", type=int, help="Timedelta of days from now")
    parser.add_argument(
        "--prefix",
        "-p",
        type=str,
        help="Top level prefix in the nextcloud path. Overwrites `NC_PREFIX` of .env",
    )

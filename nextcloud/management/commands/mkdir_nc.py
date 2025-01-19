from datetime import timedelta
from django.utils import timezone

from django.core.management.base import BaseCommand

from nextcloud import nextcloud_manager
from nextcloud.nextcloud_sync import update_observations
import logging
import nextcloud.nextcloud_manager as nm

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Creates path in the nextcloud"

    def handle(self, *args, **options):
        path = options.get("path", "").strip("/")
        nm.initialize_connection()
        nm.mkdir(path)


    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="The directory/directories to create in the nextcloud")


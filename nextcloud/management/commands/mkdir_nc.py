from django.core.management.base import BaseCommand

import logging
import nextcloud.nextcloud_manager as nm

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Creates path in the nextcloud. Example: <TURMX/Projects>"

    def handle(self, *args, **options):
        path = options.get("path", "").strip("/")
        nm.initialize_connection()
        nm.mkdir(path)

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            type=str,
            help="The directory/directories to create in the nextcloud",
        )

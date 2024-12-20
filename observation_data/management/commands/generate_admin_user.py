import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Creates a superuser with admin privileges using ADMIN_EMAIL and ADMIN_PASSWORD environment variables"

    def handle(self, *args, **options):
        """
        This command inserts a user with admin privileges
        """

        email = os.environ.get("ADMIN_EMAIL")
        password = os.environ.get("ADMIN_PASSWORD")

        if not all([email, password]):
            print("Admin credentials not set in environment variables")
            return

        self.insert_admin_user(email, password)

    @staticmethod
    def insert_admin_user(email, password):
        if User.objects.filter(email=email).exists():
            return

        user = User.objects.create_user(
            username=email, email=email, password=password, is_superuser=True
        )
        user.is_admin = True
        user.save()

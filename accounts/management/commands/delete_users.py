from django.core.management.base import BaseCommand
from django.db.models import Q

from accounts import user_data
from accounts.models import ObservatoryUser
from observation_data.observation_management import process_pending_deletion_users


class Command(BaseCommand):
    help = "Deletes all users that are marked for deletion"

    def handle(self, *args, **options):
        """
        This command deletes all users that are marked for deletion.
        It has to be called during a time that no telescope is active,
        as it will delete observations on the Nextcloud as well.
        """
        for user in ObservatoryUser.objects.filter(Q(deletion_pending=True)):
            user_data.delete_user(user)
        process_pending_deletion_users()

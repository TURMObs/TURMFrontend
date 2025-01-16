from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from authentication.models import InvitationToken


class Command(BaseCommand):
    help = "Create default groups and assign permissions"

    def handle(self, *args, **kwargs):
        # Get or create the groups
        admin_group, _ = Group.objects.get_or_create(name="admin")
        group_leader_group, _ = Group.objects.get_or_create(name="group_leader")

        # Define permissions for InvitationToken
        content_type = ContentType.objects.get_for_model(InvitationToken)

        permissions = [
            ("can_generate_invitation", "Can generate invitation links"),
            ("can_invite_admins", "Can invite new admin users"),
            ("can_invite_group_leaders", "Can invite new group leaders"),
        ]

        # Create permissions if they don't exist
        for codename, name in permissions:
            Permission.objects.get_or_create(codename=codename, content_type=content_type, defaults={"name": name})

        # Fetch permissions from the database
        can_generate_invitation = Permission.objects.get(codename="can_generate_invitation", content_type=content_type)
        can_invite_admins = Permission.objects.get(codename="can_invite_admins", content_type=content_type)
        can_invite_group_leaders = Permission.objects.get(codename="can_invite_group_leaders", content_type=content_type)

        # Assign permissions to groups
        admin_group.permissions.add(can_generate_invitation, can_invite_admins, can_invite_group_leaders)
        group_leader_group.permissions.add(can_generate_invitation, can_invite_group_leaders)


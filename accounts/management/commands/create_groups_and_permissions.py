from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import UserGroups, UserPermissions, ObservatoryUser


class Command(BaseCommand):
    help = "Create default groups and assign permissions"

    def handle(self, *args, **kwargs):
        admin_group, _ = Group.objects.get_or_create(name=UserGroups.ADMIN)
        group_leader_group, _ = Group.objects.get_or_create(
            name=UserGroups.GROUP_LEADER
        )
        user_group, _ = Group.objects.get_or_create(name=UserGroups.USER)
        content_type = ContentType.objects.get_for_model(ObservatoryUser)

        permissions = [
            (UserPermissions.CAN_GENERATE_INVITATION, "Can generate invitation links"),
            (UserPermissions.CAN_INVITE_ADMINS, "Can invite new admin users"),
            (UserPermissions.CAN_INVITE_GROUP_LEADERS, "Can invite new group leaders"),
            (
                UserPermissions.CAN_CREATE_EXPERT_OBSERVATION,
                "Can create expert observation",
            ),
        ]

        # Create permissions if they don't exist
        for codename, name in permissions:
            Permission.objects.get_or_create(
                codename=codename, content_type=content_type, defaults={"name": name}
            )

        can_generate_invitation = Permission.objects.get(
            codename=UserPermissions.CAN_GENERATE_INVITATION, content_type=content_type
        )
        can_invite_admins = Permission.objects.get(
            codename=UserPermissions.CAN_INVITE_ADMINS, content_type=content_type
        )
        can_invite_group_leaders = Permission.objects.get(
            codename=UserPermissions.CAN_INVITE_GROUP_LEADERS, content_type=content_type
        )
        can_create_expert_observation = Permission.objects.get(
            codename=UserPermissions.CAN_CREATE_EXPERT_OBSERVATION,
            content_type=content_type,
        )

        # Assign permissions to groups
        admin_group.permissions.add(
            can_generate_invitation,
            can_invite_admins,
            can_invite_group_leaders,
            can_create_expert_observation,
        )
        group_leader_group.permissions.add(can_generate_invitation)

        admin_group.save()
        group_leader_group.save()

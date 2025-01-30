from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import UserGroup, UserPermission, ObservatoryUser


class Command(BaseCommand):
    help = "Create default groups and assign permissions"

    def handle(self, *args, **kwargs):
        admin_group, _ = Group.objects.get_or_create(name=UserGroup.ADMIN)
        group_manager_group, _ = Group.objects.get_or_create(
            name=UserGroup.GROUP_MANAGER
        )
        user_group, _ = Group.objects.get_or_create(name=UserGroup.USER)
        content_type = ContentType.objects.get_for_model(ObservatoryUser)

        permissions = [
            (UserPermission.CAN_GENERATE_INVITATION, "Can generate invitation links"),
            (UserPermission.CAN_INVITE_ADMINS, "Can invite new admin users"),
            (UserPermission.CAN_INVITE_GROUP_MANAGER, "Can invite new group leaders"),
            (
                UserPermission.CAN_CREATE_EXPERT_OBSERVATION,
                "Can create expert observation",
            ),
            (UserPermission.CAN_SEE_ALL_OBSERVATIONS, "Can see all observations"),
            (UserPermission.CAN_DELETE_USERS, "Can delete users"),
            (UserPermission.CAN_EDIT_USERS, "Can edit users"),
        ]

        # Create permissions if they don't exist
        for codename, name in permissions:
            Permission.objects.get_or_create(
                codename=codename, content_type=content_type, defaults={"name": name}
            )

        can_generate_invitation = Permission.objects.get(
            codename=UserPermission.CAN_GENERATE_INVITATION, content_type=content_type
        )
        can_invite_admins = Permission.objects.get(
            codename=UserPermission.CAN_INVITE_ADMINS, content_type=content_type
        )
        can_invite_group_manager = Permission.objects.get(
            codename=UserPermission.CAN_INVITE_GROUP_MANAGER, content_type=content_type
        )
        can_create_expert_observation = Permission.objects.get(
            codename=UserPermission.CAN_CREATE_EXPERT_OBSERVATION,
            content_type=content_type,
        )
        can_see_all_observations = Permission.objects.get(
            codename=UserPermission.CAN_SEE_ALL_OBSERVATIONS, content_type=content_type
        )
        can_delete_users = Permission.objects.get(
            codename=UserPermission.CAN_DELETE_USERS, content_type=content_type
        )
        can_edit_users = Permission.objects.get(
            codename=UserPermission.CAN_EDIT_USERS, content_type=content_type
        )

        # Assign permissions to groups
        admin_group.permissions.add(
            can_generate_invitation,
            can_invite_admins,
            can_invite_group_manager,
            can_create_expert_observation,
            can_see_all_observations,
            can_delete_users,
            can_edit_users,
        )
        group_manager_group.permissions.add(can_generate_invitation)

        admin_group.save()
        group_manager_group.save()

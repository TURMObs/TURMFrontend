import uuid
from datetime import datetime
from typing import Optional

from django.contrib.auth.models import AbstractUser
from django.db import models

class UserGroups:
    ADMIN = "admin"
    GROUP_LEADER = "group_leader"
    USER = "user"

class UserPermissions:
    CAN_GENERATE_INVITATION = "can_generate_invitation"
    CAN_INVITE_ADMINS = "can_invite_admins"
    CAN_INVITE_GROUP_LEADERS = "can_invite_group_leaders"
    CAN_CREATE_EXPERT_OBSERVATION = "can_create_expert_observation"

class InvitationToken(models.Model):
    email = models.EmailField(unique=True)
    quota = models.IntegerField(null=True)
    lifetime = models.DateField(null=True)
    role = models.CharField(max_length=100, null=True, choices=[(UserGroups.ADMIN, "Admin"), (UserGroups.GROUP_LEADER, "Gruppenleiter")])
    expert = models.BooleanField(default=False)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)



class ObservatoryUser(AbstractUser):
    quota = models.IntegerField(null=True)
    lifetime = models.DateField(null=True)

    def has_quota_left(self) -> bool:
        return self.quota is None or self.quota > 0

    def has_lifetime_left(self) -> bool:
        return self.lifetime is None or self.lifetime > datetime.now()

    class Meta:
        permissions = [
            (UserPermissions.CAN_GENERATE_INVITATION, "Can generate invitation links"),
            (UserPermissions.CAN_INVITE_ADMINS, "Can invite new admin users"),
            (UserPermissions.CAN_INVITE_GROUP_LEADERS, "Can invite new group leaders"),
            (UserPermissions.CAN_CREATE_EXPERT_OBSERVATION, "Can create expert observation"),
        ]


def generate_invitation_link(
    base_url: str, email: str, quota: Optional[int] = None, lifetime: Optional[datetime] = None, role: UserGroups = UserGroups.USER, expert: bool = False
) -> Optional[str]:
    """
    Generate an invitation link for a user with a given email address.

    :param base_url: The base URL for the invitation link (e.g. http://localhost:8000/invite)
    :param email: The email address of the user to invite
    :param quota: The quota for the user. Can be None if the user has unlimited quota.
    :param lifetime: User lifetime. Can be None if the user has unlimited lifetime.
    :param role: The role of the user. Can be one of "admin", "group_leader", or "user".
    :param expert: Whether the user is an expert.

    :return: The generated invitation link, or None if a user with the given email already exists.
    """

    # Check if email is already registered
    if ObservatoryUser.objects.filter(email=email).exists():
        return None

    if InvitationToken.objects.filter(email=email).exists():
        invitation_token = InvitationToken.objects.get(email=email)
        invitation_token.quota = quota
        invitation_token.lifetime = lifetime
        invitation_token.role = role
        invitation_token.expert = expert
        invitation_token.save()
    else:
        invitation_token = InvitationToken.objects.create(
            email=email, quota=quota, lifetime=lifetime, role=role, expert=expert
        )

    invitation_link = f"{base_url}/{invitation_token.token}"
    return invitation_link

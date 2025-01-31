import uuid
from datetime import datetime
from typing import Optional

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q

from observation_data.models import AbstractObservation, ObservationStatus


class UserGroup:
    ADMIN = "admin"
    OPERATOR = "operator"
    USER = "user"


class UserPermission:
    CAN_GENERATE_INVITATION = "can_generate_invitation"
    CAN_INVITE_ADMINS = "can_invite_admins"
    CAN_INVITE_OPERATORS = "can_invite_operators"
    CAN_CREATE_EXPERT_OBSERVATION = "can_create_expert_observation"
    CAN_SEE_ALL_OBSERVATIONS = "can_see_all_observations"
    CAN_EDIT_ALL_OBSERVATIONS = "can_edit_all_observations"
    CAN_DELETE_USERS = "can_delete_users"


class InvitationToken(models.Model):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150)
    quota = models.IntegerField(null=True)
    lifetime = models.DateField(null=True)
    role = models.CharField(
        max_length=100,
        null=True,
        choices=[
            (UserGroup.ADMIN, "Admin"),
            (UserGroup.OPERATOR, "Operator"),
        ],
    )
    expert = models.BooleanField(default=False)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    link = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)


class ObservatoryUser(AbstractUser):
    quota = models.IntegerField(null=True)
    lifetime = models.DateField(null=True)
    deletion_pending = models.BooleanField(default=False)

    def has_perm(self, perm: UserPermission, obj=None):
        """
        Check if the user has a specific UserPermission. Defaults to checking for global permissions.
        """
        if super().has_perm("accounts." + str(perm)):
            return True
        return super().has_perm(str(perm), obj)

    def has_quota_left(self) -> bool:
        if self.quota is None:
            return True
        user_observations = AbstractObservation.objects.filter(user=self).filter(
            Q(project_status=ObservationStatus.PENDING)
            | Q(project_status=ObservationStatus.UPLOADED)
        )
        return self.quota > user_observations.count()

    def has_lifetime_left(self) -> bool:
        return self.lifetime is None or self.lifetime > datetime.now().date()

    def get_role(self) -> str:
        if self.groups.filter(name=UserGroup.ADMIN).exists():
            return UserGroup.ADMIN
        if self.groups.filter(name=UserGroup.OPERATOR).exists():
            return UserGroup.OPERATOR
        return UserGroup.USER

    class Meta:
        permissions = [
            (UserPermission.CAN_GENERATE_INVITATION, "Can generate invitation links"),
            (UserPermission.CAN_INVITE_ADMINS, "Can invite new admin users"),
            (UserPermission.CAN_INVITE_OPERATORS, "Can invite new operators"),
            (
                UserPermission.CAN_CREATE_EXPERT_OBSERVATION,
                "Can create expert observation",
            ),
            (UserPermission.CAN_SEE_ALL_OBSERVATIONS, "Can see all observations"),
            (UserPermission.CAN_EDIT_ALL_OBSERVATIONS, "Can edit all observations"),
        ]


def generate_invitation_link(
    base_url: str,
    email: str,
    username: Optional[str] = None,
    quota: Optional[int] = None,
    lifetime: Optional[datetime] = None,
    role: UserGroup = UserGroup.USER,
    expert: bool = False,
) -> Optional[str]:
    """
    Generate an invitation link for a user with a given email address.

    :param base_url: The base URL for the invitation link (e.g. http://localhost:8000/invite)
    :param email: The email address of the user to invite
    :param username: The username of the user to invite. Can be None if the user has no username/alias.
    :param quota: The quota for the user. Can be None if the user has unlimited quota.
    :param lifetime: User lifetime. Can be None if the user has unlimited lifetime.
    :param role: The role of the user. Can be one of "admin", "group_manager", or "user".
    :param expert: Whether the user is an expert.

    :return: The generated invitation link, or None if a user with the given email already exists.
    """

    # Check if email is already registered
    if ObservatoryUser.objects.filter(email=email).exists():
        return None

    if username is None:
        username = ""

    if InvitationToken.objects.filter(email=email).exists():
        invitation_token = InvitationToken.objects.get(email=email)
        invitation_token.username = username
        invitation_token.quota = quota
        invitation_token.lifetime = lifetime
        invitation_token.role = role
        invitation_token.expert = expert
        invitation_token.save()
    else:
        invitation_token = InvitationToken.objects.create(
            email=email,
            username=username,
            quota=quota,
            lifetime=lifetime,
            role=role,
            expert=expert,
        )

    invitation_link = f"{base_url}/{invitation_token.token}"
    invitation_token.link = invitation_link
    invitation_token.save()
    return invitation_link

import uuid
from datetime import datetime
from typing import Optional

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q

from observation_data.models import AbstractObservation, ObservationStatus


class UserGroup:
    ADMIN = "admin"
    GROUP_LEADER = "group_leader"
    USER = "user"


class UserPermission:
    CAN_GENERATE_INVITATION = "can_generate_invitation"
    CAN_INVITE_ADMINS = "can_invite_admins"
    CAN_INVITE_GROUP_LEADERS = "can_invite_group_leaders"
    CAN_CREATE_EXPERT_OBSERVATION = "can_create_expert_observation"


class InvitationToken(models.Model):
    email = models.EmailField(unique=True)
    quota = models.IntegerField(null=True)
    lifetime = models.DateField(null=True)
    role = models.CharField(
        max_length=100,
        null=True,
        choices=[
            (UserGroup.ADMIN, "Admin"),
            (UserGroup.GROUP_LEADER, "Gruppenleiter"),
        ],
    )
    expert = models.BooleanField(default=False)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ObservatoryUser(AbstractUser):
    quota = models.IntegerField(null=True)
    lifetime = models.DateField(null=True)

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

    class Meta:
        permissions = [
            (UserPermission.CAN_GENERATE_INVITATION, "Can generate invitation links"),
            (UserPermission.CAN_INVITE_ADMINS, "Can invite new admin users"),
            (UserPermission.CAN_INVITE_GROUP_LEADERS, "Can invite new group leaders"),
            (
                UserPermission.CAN_CREATE_EXPERT_OBSERVATION,
                "Can create expert observation",
            ),
        ]


def generate_invitation_link(
    base_url: str,
    email: str,
    quota: Optional[int] = None,
    lifetime: Optional[datetime] = None,
    role: UserGroup = UserGroup.USER,
    expert: bool = False,
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


SPECIAL_CHARACTERS = [
    "!",
    "#",
    "$",
    "%",
    "(",
    ")",
    "*",
    "+",
    ",",
    "-",
    ".",
    "/",
    ":",
    ";",
    "=",
    "?",
    "@",
    "[",
    "]",
    "^",
    "_",
    "{",
    "|",
    "}",
    "~",
]


def is_allowed_password(string: str) -> bool:
    """
    Check if a all characters in a string are allowed to be used in a password.

    Allowed characters: All alphanumeric, so (A-Z), (a-z), (0-9) and all characters in SPECIAL_CHARACTERS.

    :param string: The string to check.

    :return: True if the string is allowed, False otherwise.
    """

    return all(
        char.isalnum() or char in SPECIAL_CHARACTERS and char != " " for char in string
    )


def password_length_ok(string: str) -> bool:
    """
    Check if the length of a string is at least 8 characters and at most 64 characters.

    :param string: The string to check.

    :return: True if the string is at least 8 characters long and at most 64 characters long, False otherwise.
    """
    return len(string) >= 8 and len(string) <= 64


def password_requirements_met(password: str) -> bool:
    """
    Check if a password meets the requirements for a password. The password must contain at least one letter, one number and one special character.

    :param password: The password to check.

    :return: True if the password meets the requirements, False otherwise.
    """
    has_letter = any(char.isalpha() for char in password)
    has_number = any(char.isdigit() for char in password)
    has_special = any(char in SPECIAL_CHARACTERS for char in password)

    return has_letter and has_number and has_special and password_length_ok(password)

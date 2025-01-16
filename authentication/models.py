import uuid
from datetime import datetime
from typing import Optional

from django.contrib.auth.models import AbstractUser
from django.db import models


class InvitationToken(models.Model):
    email = models.EmailField(unique=True)
    quota = models.IntegerField(null=True)
    lifetime = models.DateField(null=True)
    role = models.CharField(max_length=100, null=True, choices=[("admin", "admin"), ("group_leader", "group_leader")])
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ("can_generate_invitation", "Can generate invitation links"),
            ("can_invite_admins", "Can invite new admin users"),
            ("can_invite_group_leaders", "Can invite new group leaders"),
        ]


class ObservatoryUser(AbstractUser):
    quota = models.IntegerField(null=True)
    lifetime = models.DateField(null=True)


def generate_invitation_link(
    base_url: str, email: str, quota: int, lifetime: datetime, role: str
) -> Optional[str]:
    """
    Generate an invitation link for a user with a given email address.

    :param base_url: The base URL for the invitation link (e.g. http://localhost:8000/invite)
    :param email: The email address of the user to invite
    :param quota: The quota for the user. Can be None if the user has unlimited quota.
    :param lifetime: The lifetime of the invitation link. Can be None if the user never expires.
    :param role: The role of the user. Can be one of "admin", "group_leader", or "user".

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
        invitation_token.save()
    else:
        invitation_token = InvitationToken.objects.create(
            email=email, quota=quota, lifetime=lifetime, role=role
        )

    invitation_link = f"{base_url}/{invitation_token.token}"
    return invitation_link

import uuid
from typing import Optional

from django.contrib.auth.models import User
from django.db import models


class InvitationToken(models.Model):
    email = models.EmailField(unique=True)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


def generate_invitation_link(base_url: str, email: str) -> Optional[str]:
    """
    Generate an invitation link for a user with a given email address.

    :param base_url: The base URL for the invitation link (e.g. http://localhost:8000/invite)
    :param email: The email address of the user to invite

    :return: The generated invitation link, or None if a user with the given email already exists.
    """

    # Check if email is already registered
    if User.objects.filter(email=email).exists():
        return None

    invitation_token = InvitationToken.objects.filter(email=email).first()
    if invitation_token is None:
        invitation_token = InvitationToken.objects.create(email=email)

    invitation_link = f"{base_url}/{invitation_token.token}"
    return invitation_link

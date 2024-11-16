from django.contrib.auth.models import User
from django.test import TestCase

from .models import InvitationToken, generate_invitation_link


class GenerateInvitationLinkTest(TestCase):
    def setUp(self):
        self.base_url = "http://testserver/invite/"
        self.email = "test@example.com"

    def test_generate_invitation_link_new_email(self):
        link = generate_invitation_link(self.base_url, self.email)
        self.assertIsNotNone(link)
        self.assertTrue(link.startswith(self.base_url))

        # Check that an InvitationToken was created
        token = InvitationToken.objects.get(email=self.email)
        self.assertIsNotNone(token)
        self.assertEqual(link, f"{self.base_url}{token.token}")

    def test_generate_invitation_link_existing_user(self):
        User.objects.create_user(
            username="testuser", email=self.email, password="testpass"
        )
        link = generate_invitation_link(self.base_url, self.email)
        self.assertIsNone(link)

    def test_generate_invitation_link_existing_token(self):
        # First generation
        link1 = generate_invitation_link(self.base_url, self.email)

        # Second generation with the same email
        link2 = generate_invitation_link(self.base_url, self.email)

        self.assertEqual(link1, link2)

        # Check that only one InvitationToken was created
        tokens = InvitationToken.objects.filter(email=self.email)
        self.assertEqual(tokens.count(), 1)

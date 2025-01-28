from django.test import TestCase

from .models import (
    InvitationToken,
    generate_invitation_link,
    ObservatoryUser,
    is_allowed_password,
    password_length_ok,
    password_requirements_met,
)


class GenerateInvitationLinkTest(TestCase):
    def setUp(self):
        self.base_url = "http://testserver/invite"
        self.email = "test@example.com"

    def test_generate_invitation_link_new_email(self):
        link = generate_invitation_link(self.base_url, self.email)
        self.assertIsNotNone(link)
        self.assertTrue(link.startswith(self.base_url))

        # Check that an InvitationToken was created
        token = InvitationToken.objects.get(email=self.email)
        self.assertIsNotNone(token)
        self.assertEqual(link, f"{self.base_url}/{token.token}")

    def test_generate_invitation_link_existing_user(self):
        ObservatoryUser.objects.create_user(
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


class PasswordRequirementsTest(TestCase):
    def test_is_allowed_password(self):
        # check if alphanumeric password is allowed
        self.assertTrue(is_allowed_password("TestPassword1234567890"))

        # check if password with special characters is allowed
        self.assertTrue(is_allowed_password("!#$%()*+,-./:;=?@[]^_{|}~"))

        # check if password with spaces is not allowed
        self.assertFalse(is_allowed_password(" "))
        self.assertFalse(is_allowed_password("Test Password"))

        # check if password with uncommon special characters is not allowed
        self.assertFalse(is_allowed_password("password!€"))
        self.assertFalse(is_allowed_password("password!∞"))
        self.assertFalse(is_allowed_password("password!😊"))

    def test_password_length_ok(self):
        # check if password length is at least 8 characters and at most 64 characters
        self.assertFalse(password_length_ok("test123"))
        self.assertFalse(
            password_length_ok(
                "testpasswordtestpasswordtestpasswordtestpasswordtestpassword12345"
            )
        )

        # check if empty password is not allowed
        self.assertFalse(password_length_ok(""))
        
    def test_password_requirements_met(self):
        # check if password meets the requirements for a password
        self.assertTrue(password_requirements_met("password1!"))
        self.assertFalse(password_requirements_met("password"))
        self.assertFalse(password_requirements_met("password1"))
        self.assertFalse(password_requirements_met("password!"))

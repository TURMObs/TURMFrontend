import os
import unittest

import django
from django.core.management import call_command
from django.test import TestCase
from nc_py_api import Nextcloud

from nextcloud import nextcloud_manager
from nextcloud.nextcloud_manager import (
    initialize_connection,
    mkdir,
    get_observation_file,
    file_exists,
)
from nextcloud.nextcloud_sync import upload_observations
from observation_data.models import (
    ObservationType,
    ImagingObservation,
    VariableObservation,
)
from observation_data.observation_management import (
    process_pending_deletion,
)
from .models import InvitationToken, generate_invitation_link, ObservatoryUser
import nextcloud.nextcloud_manager as nm

run_nc_test = False if os.getenv("NC_TEST", default=True) == "False" else True
prefix = os.getenv("NC_PREFIX", default="")
nc: Nextcloud


class GenerateInvitationLinkTest(TestCase):
    def setUp(self):
        self.base_url = "http://testserver/invite"
        self.email = "test@example.com"

    def test_generate_invitation_link_new_email(self):
        link = generate_invitation_link(base_url=self.base_url, email=self.email)
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


@unittest.skipIf(
    not run_nc_test,
    "Nextclouds test cannot run in CI. Set env variable `NC_TEST=True` to run nextcloud tests.",
)
class DSGVOUserDataTestCase(django.test.TestCase):
    old_prefix = ""
    prefix = nextcloud_manager.prefix
    nc_prefix = "test-nc"

    def setUp(self):
        ObservatoryUser.objects.create_user(
            username="testuser", password="testpassword", is_superuser=True
        )
        self.user = ObservatoryUser.objects.get(username="testuser")
        call_command("populate_observatories")
        self.maxDiff = None
        self.client = django.test.Client()
        self.client.force_login(user=self.user)

        # automatically adds test in name of test root folder
        self.old_prefix = self.prefix
        nextcloud_manager.prefix = f"{self.nc_prefix}{self.prefix}"
        self.prefix = f"{self.nc_prefix}{self.prefix}"

    def tearDown(self):
        nextcloud_manager.prefix = self.old_prefix

    def _create_observation(self, data: dict, user: ObservatoryUser = None):
        prev_user = self.user
        if user is not None:
            self.client.logout()
            self.client.force_login(user)
        response = self.client.post(
            path="/observation-data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.json())
        if user is not None:
            self.client.logout()
            self.client.force_login(prev_user)

    def _create_imaging_observation(
        self, target_name: str, user: ObservatoryUser = None
    ):
        data = {
            "observatory": "TURMX",
            "target": {
                "name": target_name,
                "ra": "22 32 01",
                "dec": "40 49 24",
            },
            "observation_type": ObservationType.IMAGING,
            "exposure_time": 300.0,
            "filter_set": ["R"],
            "frames_per_filter": 10,
        }
        self._create_observation(data, user)
        return ImagingObservation.objects.get(target__name=target_name)

    def _create_variable_observation(
        self, target_name: str, user: ObservatoryUser = None
    ):
        data = {
            "observatory": "TURMX",
            "target": {
                "name": target_name,
                "catalog_id": "RV-Ari",
                "ra": "02 15 07",
                "dec": "+18 04 28",
            },
            "observation_type": ObservationType.VARIABLE,
            "exposure_time": 60.0,
            "filter_set": ["L"],
            "minimum_altitude": 30.0,
            "frames_per_filter": 450,
        }
        self._create_observation(data, user)
        return VariableObservation.objects.get(target__name=target_name)

    def test_data_download(self):
        self._create_imaging_observation("M51")
        self._create_variable_observation("M42")
        response = self.client.get("/accounts/get-user-data")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("observation_requests", data)
        self.assertEqual(len(data["observation_requests"]), 2)
        self.assertIn("user", data)
        for expected_key in [
            "id",
            "is_staff",
            "is_active",
            "is_superuser",
            "last_login",
        ]:
            self.assertIn(expected_key, data["user"])
        self.assertEqual(data["user"]["username"], "testuser")
        self.assertEqual(data["user"]["password"], "PASSWORD HASH")

    def test_data_deletion(self):
        self._create_imaging_observation("M51")
        self._create_variable_observation("M42")
        self._create_imaging_observation(
            "M52",
            ObservatoryUser.objects.create_user(
                username="testuser2", password="testpassword"
            ),
        )
        response = self.client.delete(f"/accounts/delete-user/{self.user.id}")
        self.assertEqual(response.status_code, 200)
        process_pending_deletion()
        self.assertFalse(ObservatoryUser.objects.filter(username="testuser").exists())
        self.assertFalse(VariableObservation.objects.exists())
        self.assertEqual(ImagingObservation.objects.count(), 1)
        remaining_observation = ImagingObservation.objects.first()
        self.assertEqual(remaining_observation.target.name, "M52")

    def test_data_uploaded_deletion(self):
        initialize_connection()
        im1 = self._create_imaging_observation("M51")
        var1 = self._create_variable_observation("M42")
        im2 = self._create_imaging_observation(
            "M52",
            ObservatoryUser.objects.create_user(
                username="testuser2", password="testpassword"
            ),
        )
        mkdir(f"{self.prefix}/TURMX/Projects")
        upload_observations()
        file_im1 = get_observation_file(im1)
        file_var1 = get_observation_file(var1)
        file_im2 = get_observation_file(im2)
        for file in [file_im1, file_var1, file_im2]:
            self.assertIsNotNone(file)
            self.assertTrue(file_exists(file))
        response = self.client.delete(f"/accounts/delete-user/{self.user.id}")
        process_pending_deletion()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(file_exists(file_im1))
        self.assertTrue(file_exists(file_im2))
        self.assertFalse(file_exists(file_var1))
        nm.delete(f"{self.prefix}")

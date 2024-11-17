# Create your tests here.
import django.test

from observation_data.models import Observatory, CelestialTarget
from django.contrib.auth.models import User


class ObservationCreationTestCase(django.test.TestCase):
    def setUp(self):
        self.client = django.test.Client()
        # Create a user
        self.user = User.objects.create_user(
            username="testuser", password="testpassword", email="test@gmail.com"
        )
        self.client.force_login(self.user)

        # Create an observatory
        Observatory.objects.create(
            name="TURMX",
            horizon_offset=30.0,
            min_stars=10,
            max_HFR=2.0,
            max_guide_error=0.5,
            filter_set="L",
        )
        # Create a target
        CelestialTarget.objects.create(
            catalog_id="LBN437",
            name="Sagittarius A*",
            ra="17 45 40.03599",
            dec="-29 00 28.1699",
        )
        self.base_request = {
            "observatory": "TURMX",
            "target": {
                "catalog_id": "Sgr A*",
                "name": "Sagittarius A*",
                "ra": "17 45 40.03599",
                "dec": "-29 00 28.1699",
            },
            "observation_type": "Invalid",
            "exposure_time": 60.0,
            "filter_set": "L",
        }

    def test_no_user(self):
        self.client.logout()
        response = self.client.post(
            path="/observation_data/create/", data={}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403, response.json())

    def test_missing_type(self):
        response = self.client.post(
            path="/observation_data/create/", data={}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Observation type missing"})

    def test_invalid_type(self):
        response = self.client.post(
            path="/observation_data/create/",
            data={"observation_type": "Invalid"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Invalid observation type"})

    def test_missing_fields(self):
        response = self.client.post(
            path="/observation_data/create/",
            data={"type": "Imaging"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_imaging_insert(self):
        data = self.base_request
        data["observation_type"] = "Imaging"
        data["frames_per_filter"] = 1
        response = self.client.post(
            path="/observation_data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.json())

    def test_exoplanet_insert(self):
        data = self.base_request
        data["observation_type"] = "Exoplanet"
        data["start_observation"] = "2021-01-01T00:00:00Z"
        data["end_observation"] = "2021-01-01T01:00:00Z"
        response = self.client.post(
            path="/observation_data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.json())

    def test_variable_insert(self):
        data = self.base_request
        data["observation_type"] = "Variable"
        data["minimum_altitude"] = 30.0
        response = self.client.post(
            path="/observation_data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.json())

    def test_monitoring_insert(self):
        data = self.base_request
        data["observation_type"] = "Monitoring"
        data["frames_per_filter"] = 1
        data["start_scheduling"] = "2021-01-01T00:00:00Z"
        data["end_scheduling"] = "2021-01-01T01:00:00Z"
        data["cadence"] = "PT1H"
        response = self.client.post(
            path="/observation_data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.json())

    def test_expert_insert(self):
        self.user.is_staff = True
        self.user.save()
        data = self.base_request
        data["observation_type"] = "Expert"
        data["frames_per_filter"] = 1
        data["dither_every"] = 1.0
        data["binning"] = "1x1"
        data["subframe"] = "Full"
        data["gain"] = 1
        data["offset"] = 1
        data["start_observation"] = "2021-01-01T00:00:00Z"
        data["end_observation"] = "2021-01-01T01:00:00Z"
        data["start_scheduling"] = "2021-01-01T00:00:00Z"
        data["end_scheduling"] = "2021-01-01T01:00:00Z"
        data["cadence"] = "PT1H"
        data["moon_separation_angle"] = 30.0
        data["moon_separation_width"] = 30.0
        data["minimum_altitude"] = 35
        data["priority"] = 100
        response = self.client.post(
            path="/observation_data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.json())

    def test_no_expert_user(self):
        data = self.base_request
        data["observation_type"] = "Expert"
        data["frames_per_filter"] = 1
        data["dither_every"] = 1.0
        data["binning"] = "1x1"
        data["subframe"] = "Full"
        data["gain"] = 1
        response = self.client.post(
            path="/observation_data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403, response.json())

    def test_wrong_observatory(self):
        data = self.base_request
        data["observation_type"] = "Imaging"
        data["frames_per_filter"] = 1
        data["observatory"] = "INVALID"
        data["user"] = self.user.id
        response = self.client.post(
            path="/observation_data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400, response.json())

    def test_target_exists(self):
        data = self.base_request
        data["observation_type"] = "Imaging"
        data["frames_per_filter"] = 1
        data["user"] = self.user.id
        response = self.client.post(
            path="/observation_data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.json())
        response = self.client.post(
            path="/observation_data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.json())

from datetime import timezone, datetime
import django.test
from observation_data.models import Observatory, CelestialTarget
from django.contrib.auth.models import User




class ObservationCreationTestCase(django.test.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.client = django.test.Client()
        self._create_user_and_login()
        self._create_observatory_and_target()
        self.base_request = self._get_base_request()

    def _create_user_and_login(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpassword", email="test@gmail.com"
        )
        self.client.force_login(self.user)

    @staticmethod
    def _create_observatory_and_target():
        Observatory.objects.create(
            name="TURMX",
            horizon_offset=30.0,
            min_stars=10,
            max_HFR=2.0,
            max_guide_error=0.5,
            filter_set="L",
        )
        CelestialTarget.objects.create(
            catalog_id="LBN437",
            name="Sagittarius A*",
            ra="17 45 40.03599",
            dec="-29 00 28.1699",
        )

    @staticmethod
    def _get_base_request():
        return {
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

    def _send_post_request(self, data):
        return self.client.post(
            path="/observation_data/create/", data=data, content_type="application/json"
        )

    def _assert_error_response(self, response, expected_status, expected_error):
        self.assertEqual(response.status_code, expected_status, response.json())
        self.assertEqual(response.json(), expected_error)

    def test_no_user(self):
        self.client.logout()
        response = self._send_post_request({})
        self.assertEqual(response.status_code, 401, response.json())

    def test_missing_type(self):
        response = self._send_post_request({})
        self._assert_error_response(response, 400, {"error": "Observation type missing"})

    def test_invalid_type(self):
        response = self._send_post_request({"observation_type": "Invalid"})
        self._assert_error_response(response, 400, {"error": "Invalid observation type"})

    def test_missing_fields(self):
        response = self._send_post_request({"type": "Imaging"})
        self.assertEqual(response.status_code, 400)

    def _test_observation_insert(self, observation_type, additional_data=None):
        data = self.base_request.copy()
        data["observation_type"] = observation_type
        if additional_data:
            data.update(additional_data)
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 201, response.json())

    def test_imaging_insert(self):
        self._test_observation_insert("Imaging", {"frames_per_filter": 1})

    def test_exoplanet_insert(self):
        self._test_observation_insert("Exoplanet", {
            "start_observation": "2021-01-01T00:00:00Z",
            "end_observation": "2021-01-01T01:00:00Z"
        })

    def test_variable_insert(self):
        self._test_observation_insert("Variable", {"minimum_altitude": 30.0})

    def test_monitoring_insert(self):
        self._test_observation_insert("Monitoring", {
            "frames_per_filter": 1,
            "start_scheduling": "2021-01-01T00:00:00Z",
            "end_scheduling": "2021-01-01T01:00:00Z",
            "cadence": "PT1H"
        })

    def test_expert_insert(self):
        self.user.is_staff = True
        self.user.save()
        self._test_observation_insert("Expert", {
            "frames_per_filter": 1,
            "dither_every": 1.0,
            "binning": "1x1",
            "subframe": "Full",
            "gain": 1,
            "offset": 1,
            "start_observation": "2021-01-01T00:00:00Z",
            "end_observation": "2021-01-01T01:00:00Z",
            "start_scheduling": "2021-01-01T00:00:00Z",
            "end_scheduling": "2021-01-01T01:00:00Z",
            "cadence": "PT1H",
            "moon_separation_angle": 30.0,
            "moon_separation_width": 30.0,
            "minimum_altitude": 35,
            "priority": 100
        })

    def test_no_expert_user(self):
        data = self.base_request.copy()
        data["observation_type"] = "Expert"
        data["frames_per_filter"] = 1
        data["dither_every"] = 1.0
        data["binning"] = "1x1"
        data["subframe"] = "Full"
        data["gain"] = 1
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 403, response.json())

    def test_wrong_observatory(self):
        data = self.base_request.copy()
        data["observation_type"] = "Imaging"
        data["frames_per_filter"] = 1
        data["observatory"] = "INVALID"
        data["user"] = self.user.id
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 400, response.json())

    def test_target_exists(self):
        data = self.base_request.copy()
        data["observation_type"] = "Imaging"
        data["frames_per_filter"] = 1
        data["user"] = self.user.id
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 201, response.json())
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 201, response.json())

    def _test_exoplanet_overlap(self, start1, end1, start2, end2, expected_status_code):
        data = self.base_request.copy()
        data["observation_type"] = "Exoplanet"
        data["start_observation"] = start1
        data["end_observation"] = end1
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 201, response.json())

        data["start_observation"] = start2
        data["end_observation"] = end2
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, expected_status_code, response.json())

        if expected_status_code == 400:
            overlapping = response.json().get("overlapping_observations", [])
            self.assertIsInstance(overlapping, list)
            self.assertEqual(len(overlapping), 1)
            self.assertEqual(datetime.fromisoformat(overlapping[0]["start_observation"]), start1)
            self.assertEqual(datetime.fromisoformat(overlapping[0]["end_observation"]), end1)

    def test_whole_overlap_exoplanet(self):
        self._test_exoplanet_overlap(
            datetime(2020, 1, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 0, 15, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 0, 45, tzinfo=timezone.utc),
            400
        )

    def test_partial_overlap_exoplanet_end(self):
        # First test: check partial overlap from start of second observation
        self._test_exoplanet_overlap(
            datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 2, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 1, 15, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 2, 30, tzinfo=timezone.utc),
            400
        )

    def test_partial_overlap_exoplanet_start(self):
        self._test_exoplanet_overlap(
            datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 2, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 1, 15, tzinfo=timezone.utc),
            400
        )

    def test_no_overlap_exoplanet(self):
        self._test_exoplanet_overlap(
            datetime(2020, 1, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 2, 0, tzinfo=timezone.utc),
            201
        )


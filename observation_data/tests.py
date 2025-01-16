import json
import os
from datetime import datetime, timezone, timedelta

import django.test
from django.core.management import call_command
from django.conf import settings
from dotenv import load_dotenv

from authentication.models import ObservatoryUser
from observation_data.models import (
    ImagingObservation,
    ObservationType,
    Filter,
)
from observation_data.serializers import (
    ImagingObservationSerializer,
    ExoplanetObservationSerializer,
    VariableObservationSerializer,
    MonitoringObservationSerializer,
)


def _create_user_and_login(test_instance):
    load_dotenv()
    admin_username = os.getenv("ADMIN_EMAIL")
    if not admin_username:
        test_instance.fail("ADMIN_EMAIL environment variable not set")
    call_command("generate_admin_user")
    test_instance.user = ObservatoryUser.objects.get(username=admin_username)
    test_instance.client.force_login(test_instance.user)


class ObservationCreationTestCase(django.test.TestCase):
    def setUp(self):
        self.user = None
        self.client = django.test.Client()
        _create_user_and_login(self)
        call_command("populate_observatories")
        self.base_request = self._get_base_request()

    @staticmethod
    def _get_base_request():
        return {
            "observatory": "TURMX",
            "target": {
                "name": "Sagittarius A*",
                "catalog_id": "Sag A*",
                "ra": "17 45 40.03599",
                "dec": "-29 00 28.1699",
            },
            "observation_type": "Invalid",
            "exposure_time": 60.0,
            "filter_set": [Filter.FilterType.LUMINANCE],
        }

    @staticmethod
    def _get_flat_base_request():
        return {
            "observatory": "TURMX",
            "name": "Sagittarius A*",
            "catalog_id": "Sag A*",
            "ra": "17 45 40.03599",
            "dec": "-29 00 28.1699",
            "observation_type": "Invalid",
            "exposure_time": 60.0,
            "filter_set": [Filter.FilterType.LUMINANCE],
        }

    def _send_post_request(self, data):
        return self.client.post(
            path="/observation-data/create/", data=data, content_type="application/json"
        )

    def _assert_error_response(self, response, expected_status, expected_error):
        self.assertEqual(response.status_code, expected_status, response.json())
        self.assertEqual(response.json(), expected_error)

    def test_no_user(self):
        self.client.logout()
        response = self._send_post_request({})
        self.assertEqual(
            response.url, "/authentication/login?next=/observation-data/create/"
        )
        self.assertEqual(response.status_code, 302)

    def test_missing_type(self):
        response = self._send_post_request({})
        self._assert_error_response(
            response, 400, {"error": "Invalid observation type"}
        )

    def test_invalid_type(self):
        response = self._send_post_request({"observation_type": "Invalid"})
        self._assert_error_response(
            response, 400, {"error": "Invalid observation type"}
        )

    def test_invalid_type_flat(self):
        response = self._send_post_request(self._get_flat_base_request())
        self._assert_error_response(
            response, 400, {"error": "Invalid observation type"}
        )

    def test_missing_fields(self):
        response = self._send_post_request({"type": "Imaging"})
        self.assertEqual(response.status_code, 400)

    def test_missing_target_field_flat(self):
        data = self._get_flat_base_request()
        data["observation_type"] = "Imaging"
        data.pop("name")
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 400, response.json())

    def test_missing_ra_field_flat(self):
        data = self._get_flat_base_request()
        data["observation_type"] = "Imaging"
        data["frames_per_filter"] = 1
        data["required_amount"] = 100
        data.pop("ra")
        response = self._send_post_request(data)
        self._assert_error_response(
            response, 400, {"target": {"ra": ["This field is required."]}}
        )

    def _test_observation_insert(
        self, observation_type, additional_data=None, flat=False
    ):
        data = self.base_request.copy() if not flat else self._get_flat_base_request()
        data["observation_type"] = observation_type
        if additional_data:
            data.update(additional_data)
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 201, response.json())

    def test_imaging_insert(self):
        self._test_observation_insert(
            ObservationType.IMAGING, {"frames_per_filter": 100}
        )

    def test_imaging_insert_flat(self):
        self._test_observation_insert(
            ObservationType.IMAGING,
            {"frames_per_filter": 100},
            flat=True,
        )

    def test_imaging_insert_no_catalog_id(self):
        data = self.base_request.copy()
        data["observation_type"] = ObservationType.IMAGING
        data["frames_per_filter"] = 100
        data["target"].pop("catalog_id")
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 201, response.json())

    def test_imaging_insert_no_catalog_id_flat(self):
        data = self._get_flat_base_request()
        data["observation_type"] = ObservationType.IMAGING
        data["frames_per_filter"] = 100
        data.pop("catalog_id")
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 201, response.json())

    def test_exoplanet_insert(self):
        base_time = datetime.now(timezone.utc) + timedelta(days=1)
        start = base_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end = base_time.replace(hour=1, minute=0, second=0, microsecond=0)

        self._test_observation_insert(
            ObservationType.EXOPLANET,
            {
                "start_observation": start.isoformat(),
                "end_observation": end.isoformat(),
            },
        )

    def test_exoplanet_insert_flat(self):
        base_time = datetime.now(timezone.utc) + timedelta(days=1)
        start = base_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end = base_time.replace(hour=1, minute=0, second=0, microsecond=0)

        self._test_observation_insert(
            ObservationType.EXOPLANET,
            {
                "start_observation": start.isoformat(),
                "end_observation": end.isoformat(),
            },
            flat=True,
        )

    def test_variable_insert(self):
        self._test_observation_insert(
            "Variable", {"minimum_altitude": 30.0, "frames_per_filter": 100}
        )

    def test_variable_insert_flat(self):
        self._test_observation_insert(
            "Variable", {"minimum_altitude": 30.0, "frames_per_filter": 100}, flat=True
        )

    def test_monitoring_insert(self):
        self._test_observation_insert(
            ObservationType.MONITORING,
            {
                "frames_per_filter": 100,
                "start_scheduling": "2021-01-01T00:00:00Z",
                "end_scheduling": "2021-01-01T01:00:00Z",
                "cadence": 1,
            },
        )

    def test_monitoring_insert_flat(self):
        self._test_observation_insert(
            ObservationType.MONITORING,
            {
                "frames_per_filter": 100,
                "start_scheduling": "2021-01-01T00:00:00Z",
                "end_scheduling": "2021-01-01T01:00:00Z",
                "cadence": 1,
            },
            flat=True,
        )

    def test_expert_insert(self):
        base_time = datetime.now(timezone.utc) + timedelta(days=1)
        start = base_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end = base_time.replace(hour=1, minute=0, second=0, microsecond=0)

        self.user.is_superuser = True
        self.user.save()
        self._test_observation_insert(
            ObservationType.EXPERT,
            {
                "frames_per_filter": 100,
                "dither_every": 1.0,
                "binning": 1,
                "subframe": "Full",
                "gain": 1,
                "offset": 1,
                "start_observation": start.isoformat(),
                "end_observation": end.isoformat(),
                "start_scheduling": start.isoformat(),
                "end_scheduling": end.isoformat(),
                "cadence": 1,
                "moon_separation_angle": 30.0,
                "moon_separation_width": 7.0,
                "minimum_altitude": 35,
                "priority": 100,
            },
        )

    def test_expert_insert_flat(self):
        base_time = datetime.now(timezone.utc) + timedelta(days=1)
        start = base_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end = base_time.replace(hour=1, minute=0, second=0, microsecond=0)

        self.user.is_superuser = True
        self.user.save()
        self._test_observation_insert(
            ObservationType.EXPERT,
            {
                "frames_per_filter": 100,
                "dither_every": 1.0,
                "binning": 1,
                "subframe": "Full",
                "gain": 1,
                "offset": 1,
                "start_observation": start.isoformat(),
                "end_observation": end.isoformat(),
                "start_scheduling": start.isoformat(),
                "end_scheduling": end.isoformat(),
                "cadence": 1,
                "moon_separation_angle": 30.0,
                "moon_separation_width": 7.0,
                "minimum_altitude": 35,
                "priority": 100,
            },
            flat=True,
        )

    def test_no_expert_user(self):
        self.user.is_superuser = False
        self.user.save()
        data = self.base_request.copy()
        data["observation_type"] = ObservationType.EXPERT
        data["frames_per_filter"] = 1
        data["dither_every"] = 1.0
        data["binning"] = 1
        data["subframe"] = "Full"
        data["gain"] = 1
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 403, response.json())

    def test_wrong_observatory(self):
        data = self.base_request.copy()
        data["observation_type"] = ObservationType.IMAGING
        data["frames_per_filter"] = 1
        data["observatory"] = "INVALID"
        data["user"] = self.user.id
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 400, response.json())

    def test_target_exists(self):
        data = self.base_request.copy()
        data["observation_type"] = ObservationType.IMAGING
        data["frames_per_filter"] = 100
        data["user"] = self.user.id
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 201, response.json())
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 201, response.json())

    def _test_exoplanet_overlap(
        self,
        start1,
        end1,
        start2,
        end2,
        expected_status_code,
        obs1="TURMX",
        obs2="TURMX",
    ):
        data = self.base_request.copy()
        data["observation_type"] = ObservationType.EXOPLANET
        data["start_observation"] = start1
        data["end_observation"] = end1
        data["observatory"] = obs1
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 201, response.json())

        data["start_observation"] = start2
        data["end_observation"] = end2
        data["observatory"] = obs2
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, expected_status_code, response.json())

        if expected_status_code == 400:
            overlapping = response.json().get("overlapping_observations", [])
            self.assertIsInstance(overlapping, list)
            self.assertEqual(len(overlapping), 1)
            start_time = datetime.fromisoformat(overlapping[0]["start_observation"])
            end_time = datetime.fromisoformat(overlapping[0]["end_observation"])

            self.assertEqual(
                start_time.replace(tzinfo=None), start1.replace(tzinfo=None)
            )
            self.assertEqual(end_time.replace(tzinfo=None), end1.replace(tzinfo=None))

    def test_whole_overlap_exoplanet(self):
        base_time = datetime.now(timezone.utc) + timedelta(days=1)
        self._test_exoplanet_overlap(
            base_time.replace(hour=0, minute=0, second=0, microsecond=0),
            base_time.replace(hour=1, minute=0, second=0, microsecond=0),
            base_time.replace(hour=0, minute=0, second=0, microsecond=0),
            base_time.replace(hour=1, minute=0, second=0, microsecond=0),
            400,
        )

    def test_partial_overlap_exoplanet_end(self):
        base_time = datetime.now(timezone.utc) + timedelta(days=1)
        self._test_exoplanet_overlap(
            base_time.replace(hour=0, minute=0, second=0, microsecond=0),
            base_time.replace(hour=1, minute=0, second=0, microsecond=0),
            base_time.replace(hour=0, minute=30, second=0, microsecond=0),
            base_time.replace(hour=1, minute=30, second=0, microsecond=0),
            400,
        )

    def test_partial_overlap_exoplanet_start(self):
        base_time = datetime.now(timezone.utc) + timedelta(days=1)
        self._test_exoplanet_overlap(
            base_time.replace(hour=1, minute=0, second=0, microsecond=0),
            base_time.replace(hour=2, minute=0, second=0, microsecond=0),
            base_time.replace(hour=1, minute=30, second=0, microsecond=0),
            base_time.replace(hour=1, minute=45, second=0, microsecond=0),
            400,
        )

    def test_overlap_expert(self):
        base_time = datetime.now(timezone.utc) + timedelta(days=1)
        self.user.is_superuser = True
        self.user.save()
        data = self.base_request.copy()
        data["observation_type"] = ObservationType.EXPERT
        data["frames_per_filter"] = 100
        data["dither_every"] = 1.0
        data["binning"] = 1
        data["subframe"] = "Full"
        data["gain"] = 1
        data["start_observation"] = base_time.replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        data["end_observation"] = base_time.replace(
            hour=1, minute=0, second=0, microsecond=0
        ).isoformat()
        data["start_scheduling"] = base_time.replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        data["end_scheduling"] = base_time.replace(
            hour=1, minute=0, second=0, microsecond=0
        ).isoformat()
        data["cadence"] = 1
        data["moon_separation_angle"] = 30.0
        data["moon_separation_width"] = 7.0
        data["minimum_altitude"] = 35
        data["priority"] = 100
        data["offset"] = 1
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 201, response.json())

        data["start_observation"] = base_time.replace(
            hour=1, minute=30, second=0, microsecond=0
        ).isoformat()
        data["end_observation"] = base_time.replace(
            hour=2, minute=0, second=0, microsecond=0
        ).isoformat()
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 201, response.json())

        data = self.base_request.copy()
        data["observation_type"] = ObservationType.EXOPLANET
        data["start_observation"] = base_time.replace(
            hour=2, minute=5, second=0, microsecond=0
        ).isoformat()
        data["end_observation"] = base_time.replace(
            hour=2, minute=30, second=0, microsecond=0
        ).isoformat()
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 201, response.json())

        data["start_observation"] = base_time.replace(
            hour=0, minute=30, second=0, microsecond=0
        ).isoformat()
        data["end_observation"] = base_time.replace(
            hour=3, minute=30, second=0, microsecond=0
        ).isoformat()
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 400, response.json())
        self.assertEqual(len(response.json()["overlapping_observations"]), 3)

    def test_no_overlap_exoplanet(self):
        base_time = datetime.now(timezone.utc) + timedelta(days=1)
        self._test_exoplanet_overlap(
            base_time.replace(hour=0, minute=0, second=0, microsecond=0),
            base_time.replace(hour=1, minute=0, second=0, microsecond=0),
            base_time.replace(hour=1, minute=0, second=0, microsecond=0),
            base_time.replace(hour=2, minute=0, second=0, microsecond=0),
            201,
        )

    def test_overlap_different_observatory(self):
        base_time = datetime.now(timezone.utc) + timedelta(days=1)
        self._test_exoplanet_overlap(
            base_time.replace(hour=0, minute=0, second=0, microsecond=0),
            base_time.replace(hour=1, minute=0, second=0, microsecond=0),
            base_time.replace(hour=0, minute=15, second=0, microsecond=0),
            base_time.replace(hour=2, minute=0, second=0, microsecond=0),
            201,
            obs1="TURMX",
            obs2="TURMX2",
        )

    def test_invalid_ra_format(self):
        data = self._get_flat_base_request()
        data["observation_type"] = ObservationType.IMAGING
        data["ra"] = "17 45 40.1234X"
        data["frames_per_filter"] = 1
        data["required_amount"] = 100
        response = self._send_post_request(data)
        self._assert_error_response(
            response, 400, {"target": {"ra": ["Invalid format."]}}
        )

    def test_invalid_dec_format(self):
        data = self._get_flat_base_request()
        data["observation_type"] = ObservationType.IMAGING
        data["dec"] = "-29 00 28.1234X"
        data["frames_per_filter"] = 1
        data["required_amount"] = 100
        response = self._send_post_request(data)
        self._assert_error_response(
            response, 400, {"target": {"dec": ["Invalid format."]}}
        )

    def test_ra_out_of_range(self):
        data = self._get_flat_base_request()
        data["observation_type"] = ObservationType.IMAGING
        data["ra"] = "24 00 00.00000000"
        data["frames_per_filter"] = 1
        data["required_amount"] = 100
        response = self._send_post_request(data)
        self._assert_error_response(
            response, 400, {"target": {"ra": ["Invalid format."]}}
        )

    def test_dec_out_of_range(self):
        data = self._get_flat_base_request()
        data["observation_type"] = ObservationType.IMAGING
        data["dec"] = "-90 00 00.00000000"
        data["frames_per_filter"] = 1
        data["required_amount"] = 100
        response = self._send_post_request(data)
        self._assert_error_response(
            response, 400, {"target": {"dec": ["Invalid format."]}}
        )

    def test_invalid_exposure_time(self):
        data = self._get_flat_base_request()
        data["observation_type"] = ObservationType.IMAGING
        data["exposure_time"] = 31  # not a valid option
        data["frames_per_filter"] = 1
        data["required_amount"] = 100
        response = self._send_post_request(data)
        self._assert_error_response(
            response, 400, {"exposure_time": ["Must be one of [30, 60, 120, 300]."]}
        )

    def test_valid_exposure_time_expert(self):
        base_time = datetime.now(timezone.utc) + timedelta(days=1)
        data = self._get_flat_base_request()
        data["observation_type"] = ObservationType.EXPERT
        data["frames_per_filter"] = 100
        data["dither_every"] = 1.0
        data["binning"] = 1
        data["subframe"] = "Full"
        data["gain"] = 1
        data["exposure_time"] = 31  # valid because it's an expert observation
        data["start_observation"] = base_time.replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        data["end_observation"] = base_time.replace(
            hour=1, minute=0, second=0, microsecond=0
        ).isoformat()
        data["start_scheduling"] = base_time.replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        data["end_scheduling"] = base_time.replace(
            hour=1, minute=0, second=0, microsecond=0
        ).isoformat()
        data["cadence"] = 1
        data["moon_separation_angle"] = 30.0
        data["moon_separation_width"] = 7.0
        data["minimum_altitude"] = 35
        data["priority"] = 100
        data["offset"] = 1
        response = self._send_post_request(data)
        self.assertEqual(response.status_code, 201, response.json())

    def test_invalid_exposure_time_expert(self):
        base_time = datetime.now(timezone.utc) + timedelta(days=1)
        start = base_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end = base_time.replace(hour=1, minute=0, second=0, microsecond=0)

        data = self._get_flat_base_request()
        data["observation_type"] = ObservationType.EXPERT
        data["frames_per_filter"] = 1
        data["dither_every"] = 1.0
        data["binning"] = 1
        data["subframe"] = "Full"
        data["gain"] = 1
        data["exposure_time"] = 1801  # invalid because it's out of range
        data["start_observation"] = start.isoformat()
        data["end_observation"] = end.isoformat()
        data["start_scheduling"] = start.isoformat()
        data["end_scheduling"] = end.isoformat()
        data["cadence"] = 1
        data["moon_separation_angle"] = 30.0
        data["moon_separation_width"] = 7.0
        data["minimum_altitude"] = 35
        data["priority"] = 100
        data["required_amount"] = 100
        data["offset"] = 1
        response = self._send_post_request(data)
        self._assert_error_response(
            response, 400, {"exposure_time": ["Must be between 1 and 1800."]}
        )

    def test_invalid_frames_per_filter(self):
        data = self._get_flat_base_request()
        data["observation_type"] = ObservationType.IMAGING
        data["frames_per_filter"] = 10001  # Out of valid range
        response = self._send_post_request(data)
        self._assert_error_response(
            response, 400, {"frames_per_filter": ["Must be between 1 and 1000."]}
        )

    def test_missing_frames_per_filter_and_invalid_dec(self):
        data = self._get_base_request()
        data["observation_type"] = ObservationType.IMAGING
        data["target"]["dec"] = "-29 00 XX.1699"
        response = self._send_post_request(data)

        self._assert_error_response(
            response,
            400,
            {
                "target": {"dec": ["Invalid format."]},
                "frames_per_filter": ["This field is required."],
            },
        )

    # noinspection PyTypedDict
    def test_invalid_filter(self):
        data = self._get_flat_base_request()
        data["observation_type"] = ObservationType.IMAGING
        data["frames_per_filter"] = 1
        data["required_amount"] = 100
        data["filter_set"] = ["X"]
        response = self._send_post_request(data)
        self._assert_error_response(
            response, 400, {"filter_set": ['Invalid pk "X" - object does not exist.']}
        )

    def test_missing_filters(self):
        data = self._get_flat_base_request()
        data["observation_type"] = ObservationType.IMAGING
        data["frames_per_filter"] = 1
        data["required_amount"] = 100
        data.pop("filter_set")
        response = self._send_post_request(data)
        self._assert_error_response(
            response, 400, {"filter_set": ["This field is required."]}
        )

    def test_unavailable_filters(self):
        data = self._get_flat_base_request()
        data["observation_type"] = ObservationType.IMAGING
        data["frames_per_filter"] = 1
        data["required_amount"] = 100
        data["filter_set"] = [
            Filter.FilterType.SLOAN_R,
            Filter.FilterType.SLOAN_I,
            Filter.FilterType.LUMINANCE,
        ]
        response = self._send_post_request(data)
        self._assert_error_response(
            response,
            400,
            {
                "filter_set": [
                    "Filter SR is not available at observatory TURMX.",
                    "Filter SI is not available at observatory TURMX.",
                ]
            },
        )

    def test_multiple_errors(self):
        data = self._get_flat_base_request()
        data["observation_type"] = ObservationType.EXOPLANET
        data["frames_per_filter"] = 1
        data["required_amount"] = -1
        data["filter_set"] = [Filter.FilterType.RED]
        data["start_observation"] = "2021-01-01T01:00:00Z"
        data["end_observation"] = "2021-01-01T00:00:00Z"
        response = self._send_post_request(data)
        self._assert_error_response(
            response,
            400,
            {
                "time_range": ["Start time must be before end time."],
                "start_time": ["Start time must be in the future."],
            },
        )


class JsonFormattingTestCase(django.test.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.user = None
        self.client = django.test.Client()
        _create_user_and_login(self)
        try:
            call_command("populate_observatories")
            self._create_imaging_observations()
            self._create_exoplanet_observation()
            self._create_monitoring_observation()
            self._create_variable_observation()
        except Exception as e:
            self.fail(f"Failed to create test data: {e}")

    def _create_imaging_observations(self):
        data = {
            "observatory": "TURMX",
            "target": {
                "name": "LBN437",
                "ra": "22 32 01",
                "dec": "40 49 24",
            },
            "observation_type": ObservationType.IMAGING,
            "exposure_time": 300.0,
            "filter_set": ["H"],
            "frames_per_filter": 100,
        }
        response = self.client.post(
            path="/observation-data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.json())

        data = {
            "observatory": "TURMX",
            "target": {
                "name": "NGC7822",
                "ra": "00 02 29",
                "dec": "67 10 02",
            },
            "observation_type": ObservationType.IMAGING,
            "exposure_time": 300.0,
            "filter_set": ["H", "O", "S"],
            "frames_per_filter": 100,
        }
        response = self.client.post(
            path="/observation-data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.json())

    def _create_exoplanet_observation(self):
        base_time = datetime.now(timezone.utc) + timedelta(days=1)
        data = {
            "observatory": "TURMX",
            "target": {
                "name": "Qatar-4b",
                "ra": "00 19 26",
                "dec": "+44 01 39",
            },
            "observation_type": ObservationType.EXOPLANET,
            "start_observation": base_time.replace(
                hour=19, minute=30, second=0
            ).isoformat(),
            "end_observation": base_time.replace(
                hour=23, minute=30, second=0
            ).isoformat(),
            "exposure_time": 120.0,
            "filter_set": ["L"],
        }
        response = self.client.post(
            path="/observation-data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.json())

    def _create_monitoring_observation(self):
        base_time = datetime.now(timezone.utc) + timedelta(days=1)
        data = {
            "observatory": "TURMX",
            "target": {
                "name": "T-CrB",
                "ra": "15 59 30",
                "dec": "+25 55 13",
            },
            "cadence": 1,
            "exposure_time": 30.0,
            "start_scheduling": base_time.replace(
                hour=22, minute=0, second=0
            ).isoformat(),
            "end_scheduling": (base_time + timedelta(days=2))
            .replace(hour=23, minute=0, second=0)
            .isoformat(),
            "observation_type": ObservationType.MONITORING,
            "filter_set": ["R", "G", "B"],
            "frames_per_filter": 10,
        }
        response = self.client.post(
            path="/observation-data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.json())

    def _create_variable_observation(self):
        data = {
            "observatory": "TURMX",
            "target": {
                "name": "RV-Ari",
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
        response = self.client.post(
            path="/observation-data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.json())

    def _assert_deep_dict_equal(self, dict1, dict2, path=""):
        errors = []

        if path == "":
            if "id" not in dict1:
                errors.append("Key 'id' is missing in the actual dictionary.")
            else:
                load_dotenv()
                admin_username = os.getenv("ADMIN_EMAIL")
                if dict1["id"] != admin_username:
                    errors.append(
                        f"ID mismatch: expected {admin_username}, got {dict1['id']}"
                    )
            dict1.pop("id")
            dict2.pop("id")

        if isinstance(dict1, list) and isinstance(dict2, list):
            if len(dict1) != len(dict2):
                errors.append(
                    f"List length mismatch at '{path}': expected length {len(dict1)}, got {len(dict2)}"
                )
            for idx, (item1, item2) in enumerate(zip(dict1, dict2)):
                errors.extend(
                    self._assert_deep_dict_equal(item1, item2, f"{path}[{idx}]")
                )
        elif isinstance(dict1, dict) and isinstance(dict2, dict):
            for key in dict2:
                current_path = f"{path}.{key}" if path else key
                if key not in dict1:
                    errors.append(
                        f"Key '{current_path}' is missing in the actual dictionary."
                    )
                else:
                    errors.extend(
                        self._assert_deep_dict_equal(
                            dict1[key], dict2[key], current_path
                        )
                    )

            for key in dict1:
                current_path = f"{path}.{key}" if path else key
                if key not in dict2:
                    errors.append(
                        f"Key '{current_path}' is not in the expected dictionary."
                    )
        else:
            if dict1 != dict2:
                errors.append(
                    f"Value mismatch at '{path}': expected {dict2}, got {dict1}"
                )

        if path == "":
            if errors:
                raise AssertionError("\n".join(errors))

        return errors

    def _test_serialization(
        self, target_name, serializer_class, file_name, remove_start_end=False
    ):
        serializer = serializer_class(
            serializer_class.Meta.model.objects.get(target__name=target_name)
        )
        json_representation = serializer.data
        file_path = os.path.join(
            settings.BASE_DIR, "observation_data", "test_data", file_name
        )
        with open(file_path, "r") as file:
            expected_json = json.load(file)
            if remove_start_end:
                expected_json["targets"][0].pop("startDateTime")
                expected_json["targets"][0].pop("endDateTime")
                json_representation["targets"][0].pop("startDateTime")
                json_representation["targets"][0].pop("endDateTime")
            self._assert_deep_dict_equal(json_representation, expected_json)

    def test_observation_exists(self):
        observation = ImagingObservation.objects.get(target__name="LBN437")
        self.assertIsNotNone(observation)

    def test_json_imaging_formatting(self):
        self._test_serialization(
            "LBN437", ImagingObservationSerializer, "Imaging_H_LBN437.json"
        )
        self._test_serialization(
            "NGC7822", ImagingObservationSerializer, "Imaging_HOS_NGC7822.json"
        )

    def test_json_exoplanet_formatting(self):
        self._test_serialization(
            "Qatar-4b",
            ExoplanetObservationSerializer,
            "Exoplanet_L_Qatar-4b.json",
            True,
        )

    def test_json_monitoring_formatting(self):
        self._test_serialization(
            "T-CrB", MonitoringObservationSerializer, "Monitor_RGB_T-CrB.json"
        )

    def test_json_variable_formatting(self):
        self._test_serialization(
            "RV-Ari", VariableObservationSerializer, "Variable_L_RV-Ari.json"
        )

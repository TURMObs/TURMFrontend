import json
import os
from datetime import timezone, datetime

import django.test
from django.core.management import call_command
from django.conf import settings
from django.contrib.auth.models import User

from observation_data.models import (
    ImagingObservation, ObservationType,
)
from observation_data.serializers import (
    ImagingObservationSerializer,
    ExoplanetObservationSerializer,
    VariableObservationSerializer,
    MonitoringObservationSerializer, ObservatorySerializer,
)


class ObservationCreationTestCase(django.test.TestCase):
    def setUp(self):
        self.client = django.test.Client()
        self._create_user_and_login()
        self._create_base_data()
        self.base_request = self._get_base_request()

    def _create_user_and_login(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpassword", email="test@gmail.com"
        )
        self.client.force_login(self.user)

    @staticmethod
    def _create_base_data():
        call_command("populate_observatories")

    @staticmethod
    def _get_base_request():
        return {
            "observatory": "TURMX",
            "target": {
                "name": "Sagittarius A*",
                "ra": "17 45 40.03599",
                "dec": "-29 00 28.1699",
            },
            "observation_type": "Invalid",
            "exposure_time": 60.0,
            "filter_set": ["L"],
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
        self._assert_error_response(
            response, 400, {"error": "Observation type missing"}
        )

    def test_invalid_type(self):
        response = self._send_post_request({"observation_type": "Invalid"})
        self._assert_error_response(
            response, 400, {"error": "Invalid observation type"}
        )

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
        self._test_observation_insert(ObservationType.IMAGING, {"frames_per_filter": 1, "required_amount": 100})

    def test_exoplanet_insert(self):
        self._test_observation_insert(
            ObservationType.EXOPLANET,
            {
                "start_observation": "2021-01-01T00:00:00Z",
                "end_observation": "2021-01-01T01:00:00Z",
            },
        )

    def test_variable_insert(self):
        self._test_observation_insert("Variable", {"minimum_altitude": 30.0, "required_amount": 100})

    def test_monitoring_insert(self):
        self._test_observation_insert(
            ObservationType.MONITORING,
            {
                "frames_per_filter": 1,
                "start_scheduling": "2021-01-01T00:00:00Z",
                "end_scheduling": "2021-01-01T01:00:00Z",
                "cadence": 1,
                "required_amount": 100,
            },
        )

    def test_expert_insert(self):
        self.user.is_superuser = True
        self.user.save()
        self._test_observation_insert(
            ObservationType.EXPERT,
            {
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
                "cadence": 1,
                "moon_separation_angle": 30.0,
                "moon_separation_width": 30.0,
                "minimum_altitude": 35,
                "priority": 100,
                "required_amount": 100,
            },
        )

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
        data["required_amount"] = 100
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
            start_time = datetime.fromisoformat(
                overlapping[0]["targets"][0]["startDateTime"]
            )
            end_time = datetime.fromisoformat(
                overlapping[0]["targets"][0]["endDateTime"]
            )

            self.assertEqual(
                start_time.replace(tzinfo=None), start1.replace(tzinfo=None)
            )
            self.assertEqual(end_time.replace(tzinfo=None), end1.replace(tzinfo=None))

    def test_whole_overlap_exoplanet(self):
        self._test_exoplanet_overlap(
            datetime(2020, 1, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 0, 15, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 0, 45, tzinfo=timezone.utc),
            400,
        )

    def test_partial_overlap_exoplanet_end(self):
        # First test: check partial overlap from start of second observation
        self._test_exoplanet_overlap(
            datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 2, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 1, 15, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 2, 30, tzinfo=timezone.utc),
            400,
        )

    def test_partial_overlap_exoplanet_start(self):
        self._test_exoplanet_overlap(
            datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 2, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 1, 15, tzinfo=timezone.utc),
            400,
        )

    def test_no_overlap_exoplanet(self):
        self._test_exoplanet_overlap(
            datetime(2020, 1, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 1, 2, 0, tzinfo=timezone.utc),
            201,
        )


class JsonFormattingTestCase(django.test.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.client = django.test.Client()
        self._create_user_and_login()
        try:
            self._create_base_data()
            self._create_imaging_observations()
            self._create_exoplanet_observation()
            self._create_monitoring_observation()
            self._create_variable_observation()
        except Exception as e:
            self.fail(f"Failed to create test data: {e}")

    def _create_user_and_login(self):
        self.user = User.objects.create_user(
            username="JsonTest", password="JsonTest", email="JsonTest@gmail.com"
        )
        self.user.is_superuser = True
        self.client.force_login(self.user)

    @staticmethod
    def _create_base_data():
        call_command("populate_observatories")

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
            "frames_per_filter": 1,
            "required_amount": 100
        }
        response = self.client.post(
            path="/observation_data/create/", data=data, content_type="application/json"
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
            "frames_per_filter": 1.0,
            "required_amount": 100
        }
        response = self.client.post(
            path="/observation_data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.json())

    def _create_exoplanet_observation(self):
        data = {
            "observatory": "TURMX",
            "target": {
                "name": "Qatar-4b",
                "ra": "00 19 26",
                "dec": "+44 01 39",
            },
            "observation_type": ObservationType.EXOPLANET,
            "start_observation": "2024-10-25T19:30:00",
            "end_observation": "2024-10-25T23:40:00",
            "exposure_time": 120.0,
            "filter_set": ["L"],
        }
        response = self.client.post(
            path="/observation_data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.json())

    def _create_monitoring_observation(self):
        data = {
            "observatory": "TURMX",
            "target": {
                "name": "T-CrB",
                "ra": "15 59 30",
                "dec": "+25 55 13",
            },
            "cadence": 1,
            "exposure_time": 30.0,
            "start_scheduling": "2024-10-25T19:30:00",
            "end_scheduling": "2024-10-25T23:40:00",
            "observation_type": ObservationType.MONITORING,
            "frames_per_filter": 1.0,
            "filter_set": ["R", "G", "B"],
            "required_amount": 10
        }
        response = self.client.post(
            path="/observation_data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.json())

    def _create_variable_observation(self):
        data = {
            "observatory": "TURMX",
            "target": {
                "name": "RV-Ari",
                "ra": "02 15 07",
                "dec": "+18 04 28",
            },
            "observation_type": ObservationType.VARIABLE,
            "exposure_time": 60.0,
            "filter_set": ["L"],
            "minimum_altitude": 30.0,
            "required_amount": 450
        }
        response = self.client.post(
            path="/observation_data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.json())

    def _assert_deep_dict_equal(self, dict1, dict2, path="", remove_id=False):
        errors = []

        if remove_id:
            if "id" not in dict1:
                errors.append("Key 'id' is missing in the actual dictionary.")
            else:
                dict1.pop("id", None)
                dict2.pop("id", None)

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

    def _test_serialization(self, target_name, serializer_class, file_name):
        serializer = serializer_class(
            serializer_class.Meta.model.objects.get(target__name=target_name)
        )
        json_representation = serializer.data
        file_path = os.path.join(
            settings.BASE_DIR, "observation_data", "test_data", file_name
        )
        # save the json representation to a file for manual inspection
        with open(file_path.replace(".json", "_actual.json"), "w") as file:
            json.dump(json_representation, file, indent=4)

        with open(file_path, "r") as file:
            expected_json = json.load(file)
            self._assert_deep_dict_equal(
                json_representation, expected_json, remove_id=True
            )

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
            "Qatar-4b", ExoplanetObservationSerializer, "Exoplanet_L_Qatar-4b.json"
        )

    def test_json_monitoring_formatting(self):
        self._test_serialization(
            "T-CrB", MonitoringObservationSerializer, "Monitor_RGB_T-CrB.json"
        )

    def test_json_variable_formatting(self):
        self._test_serialization(
            "RV-Ari", VariableObservationSerializer, "Variable_L_RV-Ari.json"
        )

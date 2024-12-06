import filecmp
import json
import unittest
import django
import django.test
from django.contrib.auth.models import User
from nc_py_api import NextcloudException
from django.core.management import call_command
from nextcloud import nextcloud_manager as nm
from nextcloud.nextcloud_upload import upload_observations, build_nextcloud_path
from observation_data.models import AbstractObservation, ObservationType
from observation_data.serializers import get_serializer

file_upload = "nextcloud/test_data/upload_file.json"
file_download = "nextcloud/test_data/download_file.json"
file_nc = "file1.json"

dict_upload = "nextcloud/test_data/upload_dict.json"
dict_download = "nextcloud/test_data/download_dict.json"
dict_nc = "dict1.json"


class NextcloudManagerTestCaseWithoutInit(unittest.TestCase):
    def test_access_nc_without_init(self):
        with self.assertRaises(Exception):
            nm.delete("/does/not/matter")


class NextcloudManagerTestCase(django.test.TestCase):
    def setUp(self):
        nm.initialize_connection()

        self.LOCAL_PATH = "test_data"

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

        nm._delete_all()

    def _create_user_and_login(self):
        self.user = User.objects.create_user(
            username="JsonTest", password="JsonTest", email="JsonTest@gmail.com"
        )
        self.user.is_superuser = True
        self.client.force_login(self.user)

    def _create_base_data(self):
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
            "required_amount": 100,
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
            "required_amount": 100,
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
            "exposure_time": 300.0,
            "start_scheduling": "2024-10-25T19:30:00",
            "end_scheduling": "2024-10-25T23:40:00",
            "observation_type": ObservationType.MONITORING,
            "frames_per_filter": 1.0,
            "filter_set": ["R", "G", "B"],
            "required_amount": 100,
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
            "exposure_time": 300.0,
            "filter_set": ["L"],
            "minimum_altitude": 30.0,
            "required_amount": 100,
        }
        response = self.client.post(
            path="/observation_data/create/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.json())

    def test_nc_upload_and_download(self):
        nm.upload_file(file_nc, file_upload)
        nm.download_file(file_nc, file_download)
        are_eq = filecmp.cmp(file_upload, file_download, shallow=False)
        self.assertTrue(are_eq)
        nm.delete(file_nc)

    def test_nc_upload_and_download_dict(self):
        with open(dict_upload, "r") as f:
            data = json.load(f)

        nm.upload_dict(dict_nc, data)
        res_dict = nm.download_dict(dict_nc)

        with open(dict_download, "w") as f:
            json.dump(res_dict, f, indent=2)

        are_eq = filecmp.cmp(dict_upload, dict_download, shallow=False)
        self.assertTrue(are_eq)
        nm.delete(dict_nc)

    def test_upload_to_non_existing_folder(self):
        with self.assertRaises(Exception):
            nm.upload_file("non/existing/path"+file_nc, file_upload)

    def test_delete(self):
        nm.upload_file("delete_test.json", file_upload)
        nm.delete("delete_test.json")
        try:
            nm.delete("non_existent_file.json")
        except Exception:
            self.assertRaises(NextcloudException)

    def test_mkdir_simple(self):
        try:
            nm.mkdir("mkdir_test")
            nm.upload_file("mkdir_test/mkdir_test.json", file_upload) # throws error if directory does not exist
            nm.delete("mkdir_test")
        except Exception:
            self.assertRaises(NextcloudException)

    def test_mkdir_complex(self):
        try:
            path = "this/is/a/long/path/"
            nm.mkdir("this/is/test")
            nm.mkdir(path)
            nm.upload_file(path+file_nc, file_upload)
            nm.delete("this")
        except Exception:
            self.assertRaises(NextcloudException)

    def test_upload_from_db(self):
        nm.mkdir("TURMX/Projects")
        nm.mkdir("TURMX2/Projects")
        observations = AbstractObservation.objects.filter(
            project_status=AbstractObservation.ObservationStatus.PENDING
        )
        paths = []
        for observation in observations:
            obs_dict = get_serializer(observation.observation_type)(observation).data

            paths.append(build_nextcloud_path(observation, obs_dict["name"]))

        upload_observations()

        for path in paths:
            nm.delete(path)  # throws error if not existent

        self.assertEqual(
            len(
                AbstractObservation.objects.filter(
                    project_status=AbstractObservation.ObservationStatus.PENDING
                )
            ),
            0,
        )
        self.assertEqual(
            len(
                AbstractObservation.objects.filter(
                    project_status=AbstractObservation.ObservationStatus.ERROR
                )
            ),
            0,
        )
        self.assertEqual(
            len(
                AbstractObservation.objects.filter(
                    project_status=AbstractObservation.ObservationStatus.UPLOADED
                )
            ),
            len(observations),
        )
        nm.delete("TURMX/Projects")
        nm.delete("TURMX2/Projects")


import django
from django.utils import timezone
from django.core.management import call_command
import django.test
from nc_py_api import NextcloudException

from nextcloud import nextcloud_manager as nm, nextcloud_manager
from accounts.models import ObservatoryUser
from nextcloud.nextcloud_manager import file_exists, generate_observation_path
from nextcloud.nextcloud_sync import (
    upload_observations,
    calc_progress,
    update_observations,
)

import filecmp
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import unittest

from observation_data.models import (
    ObservationType,
    ObservationStatus,
    CelestialTarget,
    Filter,
    Observatory,
    AbstractObservation,
    ImagingObservation,
    ExoplanetObservation,
    VariableObservation,
    MonitoringObservation,
    ExpertObservation,
)
from observation_data.serializers import get_serializer

file_upload = "nextcloud/test_data/upload_file.json"
file_download = "nextcloud/test_data/download_file.json"
file_nc = "file1_test.json"

dict_upload = "nextcloud/test_data/upload_dict.json"
dict_download = "nextcloud/test_data/download_dict.json"
dict_nc = "dict1_test.json"

run_nc_test = False if os.getenv("NC_TEST", default=True) == "False" else True


@unittest.skipIf(
    not run_nc_test,
    "Nextclouds test cannot run in CI. Set env variable `NC_TEST=True` to run nextcloud tests.",
)
class NextcloudManagerTestCaseWithoutInit(django.test.TestCase):
    def test_access_nc_without_init(self):
        self.client = django.test.Client()
        with self.assertRaises(Exception):
            nm.delete("/does/not/matter")


# noinspection DuplicatedCode
@unittest.skipIf(
    not run_nc_test,
    "Nextclouds test cannot run in CI. Set env variable `NC_TEST=True` to run nextcloud tests.",
)
class NextcloudManagerTestCase(django.test.TestCase):
    old_prefix = ""
    prefix = nextcloud_manager.prefix
    nc_prefix = "test-nc"

    def setUp(self):
        nm.initialize_connection()

        self.maxDiff = None
        self.client = django.test.Client()
        self.user = None

        # automatically adds test in name of test root folder
        self.old_prefix = self.prefix
        nextcloud_manager.prefix = f"{self.nc_prefix}{self.prefix}"
        self.prefix = f"{self.nc_prefix}{self.prefix}"

    def tearDown(self):
        nextcloud_manager.prefix = self.old_prefix

    def test_nc_upload_and_download(self):
        nm.upload_file(file_nc, file_upload)
        nm.download_file(file_nc, file_download)
        are_eq = filecmp.cmp(file_upload, file_download, shallow=False)
        self.assertTrue(are_eq)
        nm.delete(file_nc)

    # noinspection PyTypeChecker
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
            nm.upload_file("non/existing/path" + file_nc, file_upload)

    def test_delete(self):
        nm.upload_file("delete_test.json", file_upload)
        nm.delete("delete_test.json")
        with self.assertRaises(Exception):
            nm.delete("delete_test.json")

    def test_mkdir_simple(self):
        nm.mkdir("mkdir_test")
        nm.upload_file(
            "mkdir_test/mkdir_test.json", file_upload
        )  # throws error if directory does not exist
        nm.delete("mkdir_test")

    def test_mkdir_complex(self):
        path = f"{self.prefix}/this/is/a/long/path/"
        nm.mkdir(path)
        nm.upload_file(
            path + file_nc, file_upload
        )  # throws exception if folder does not exist
        nm.delete(self.prefix)

    def test_file_exists(self):
        nm.mkdir(f"{self.prefix}/file/exists")
        nm.upload_file(f"{self.prefix}/file/exists/test.json", file_upload)
        self.assertTrue(file_exists(f"{self.prefix}/file/exists/test.json"))
        self.assertFalse(file_exists(f"{self.prefix}/file/exists/test_again.json"))
        self.assertFalse(file_exists(f"{self.prefix}/file"))
        nm.delete(self.prefix)


@unittest.skipIf(
    not run_nc_test,
    "Nextclouds test cannot run in CI. Set env variable `NC_TEST=True` to run nextcloud tests.",
)
class NextcloudSyncTestCase(django.test.TestCase):
    old_prefix = ""
    prefix = nextcloud_manager.prefix
    nc_prefix = "test-nc"

    def setUp(self):
        nm.initialize_connection()
        call_command("populate_observatories")

        self.maxDiff = None
        self.client = django.test.Client()
        self.user = None
        self._create_user_and_login()

        # automatically adds test in name of test root folder
        self.old_prefix = self.prefix
        nextcloud_manager.prefix = f"{self.nc_prefix}{self.prefix}"
        self.prefix = f"{self.nc_prefix}{self.prefix}"
        try:
            nextcloud_manager.delete(self.prefix)
            nextcloud_manager.mkdir(self.prefix)
        except NextcloudException:
            pass

    def tearDown(self):
        nextcloud_manager.prefix = self.old_prefix

    # noinspection DuplicatedCode
    def _create_imaging_observations(
        self,
        obs_id: int,
        observatory: Observatory,
        target_name: str = "TestTargetImaging",
        target_ra: str = "0",
        target_dec: str = "0",
        project_status: ObservationStatus = ObservationStatus.PENDING,
        project_completion: float = 0.0,
        priority: int = 1,
        exposure_time: float = 10.0,
        frames_per_filter: int = 10,
        second_filter: bool = False,
    ):
        """
        Creates imaging observations from scratch without checks from serializers
        """
        target = CelestialTarget.objects.create(
            name=target_name, ra=target_ra, dec=target_dec
        )

        obs = ImagingObservation.objects.create(
            id=obs_id,
            observatory=observatory,
            target=target,
            user=self.user,
            created_at=timezone.now(),
            observation_type=ObservationType.IMAGING,
            project_status=project_status,
            project_completion=project_completion,
            priority=priority,
            exposure_time=exposure_time,
            frames_per_filter=frames_per_filter,
        )

        obs.filter_set.add(Filter.objects.get(filter_type=Filter.FilterType.LUMINANCE))
        if second_filter:
            obs.filter_set.add(Filter.objects.get(filter_type=Filter.FilterType.BLUE))

    # noinspection DuplicatedCode
    def _create_exoplanet_observation(
        self,
        obs_id: int,
        observatory: Observatory,
        target_name: str = "TestTargetExoplanet",
        target_ra: str = "0",
        target_dec: str = "0",
        project_status: ObservationStatus = ObservationStatus.PENDING,
        project_completion: float = 0.0,
        priority: int = 1,
        exposure_time: float = 10.0,
        start_observation: datetime = (timezone.now()),
        end_observation: datetime = (timezone.now() + timedelta(days=1)),
    ):
        """
        Creates exoplanet observations from scratch without checks from serializers. Sets today as start and tomorrow as default start/end times.
        """
        target = CelestialTarget.objects.create(
            name=target_name, ra=target_ra, dec=target_dec
        )

        obs = ExoplanetObservation.objects.create(
            id=obs_id,
            observatory=observatory,
            target=target,
            user=self.user,
            created_at=timezone.now(),
            observation_type=ObservationType.EXOPLANET,
            project_status=project_status,
            project_completion=project_completion,
            priority=priority,
            exposure_time=exposure_time,
            start_observation=start_observation,
            end_observation=end_observation,
        )

        obs.filter_set.add(Filter.objects.get(filter_type=Filter.FilterType.LUMINANCE))

    # noinspection DuplicatedCode
    def _create_variable_observation(
        self,
        obs_id: int,
        observatory: Observatory,
        target_name: str = "TestTargetVariable",
        target_ra: str = "0",
        target_dec: str = "0",
        project_status: ObservationStatus = ObservationStatus.PENDING,
        project_completion: float = 0.0,
        priority: int = 1,
        exposure_time: float = 10.0,
        minimum_altitude: float = 10.0,
        frames_per_filter: int = 100,
    ):
        """
        Creates variable observations from scratch without checks from serializers
        """
        target = CelestialTarget.objects.create(
            name=target_name, ra=target_ra, dec=target_dec
        )

        obs = VariableObservation.objects.create(
            id=obs_id,
            observatory=observatory,
            target=target,
            user=self.user,
            created_at=timezone.now(),
            observation_type=ObservationType.VARIABLE,
            project_status=project_status,
            project_completion=project_completion,
            priority=priority,
            exposure_time=exposure_time,
            minimum_altitude=minimum_altitude,
            frames_per_filter=frames_per_filter,
        )

        obs.filter_set.add(Filter.objects.get(filter_type=Filter.FilterType.LUMINANCE))

    def _create_monitoring_observation(
        self,
        obs_id: int,
        observatory: Observatory,
        target_name: str = "TestTargetMonitoring",
        target_ra: str = "0",
        target_dec: str = "0",
        project_status: ObservationStatus = ObservationStatus.PENDING,
        project_completion: float = 0.0,
        priority: int = 1,
        exposure_time: float = 10.0,
        start_scheduling: datetime.date = timezone.now().date(),
        end_scheduling: datetime.date = timezone.now().date() + timedelta(days=1),
        frames_per_filter: int = 10,
        cadence: int = 1,
    ):
        """
        Creates monitoring observations from scratch without checks from serializers
        """
        target = CelestialTarget.objects.create(
            name=target_name, ra=target_ra, dec=target_dec
        )

        obs = MonitoringObservation.objects.create(
            id=obs_id,
            observatory=observatory,
            target=target,
            user=self.user,
            created_at=timezone.now(),
            observation_type=ObservationType.MONITORING,
            project_status=project_status,
            project_completion=project_completion,
            priority=priority,
            exposure_time=exposure_time,
            start_scheduling=start_scheduling,
            end_scheduling=end_scheduling,
            next_upload=start_scheduling,
            cadence=cadence,
            frames_per_filter=frames_per_filter,
        )

        obs.filter_set.add(Filter.objects.get(filter_type=Filter.FilterType.LUMINANCE))

    def _create_expert_observation(
        self,
        obs_id: int,
        observatory: Observatory,
        target_name: str = "TestTargetExpert",
        target_ra: str = "0",
        target_dec: str = "0",
        project_status: ObservationStatus = ObservationStatus.PENDING,
        project_completion: float = 0.0,
        priority: int = 1,
        exposure_time: float = 10.0,
        start_scheduling: datetime.date = timezone.now().date(),
        end_scheduling: datetime.date = timezone.now().date() + timedelta(days=1),
        dither_every: float = 10.0,
        binning: int = 1,
        gain: int = 10,
        offset: float = 10,
        start_observation: datetime = timezone.now(),
        end_observation: datetime = (timezone.now() + timedelta(days=1)),
        cadence: int = 1,
        moon_separation_angle: float = 10.0,
        moon_separation_width: int = 1,
        minimum_altitude: float = 10.0,
        frames_per_filter: int = 100,
        subframe: int = 1,
    ):
        """
        Creates expert observations from scratch without checks from serializers
        """
        target = CelestialTarget.objects.create(
            name=target_name, ra=target_ra, dec=target_dec
        )

        obs = ExpertObservation.objects.create(
            id=obs_id,
            observatory=observatory,
            target=target,
            user=self.user,
            created_at=timezone.now(),
            observation_type=ObservationType.EXPERT,
            project_status=project_status,
            project_completion=project_completion,
            priority=priority,
            exposure_time=exposure_time,
            start_scheduling=start_scheduling,
            end_scheduling=end_scheduling,
            next_upload=start_scheduling,
            dither_every=dither_every,
            binning=binning,
            gain=gain,
            offset=offset,
            start_observation=start_observation,
            end_observation=end_observation,
            cadence=cadence,
            moon_separation_angle=moon_separation_angle,
            moon_separation_width=moon_separation_width,
            minimum_altitude=minimum_altitude,
            frames_per_filter=frames_per_filter,
            subframe=subframe,
        )

        obs.filter_set.add(Filter.objects.get(filter_type=Filter.FilterType.LUMINANCE))

    @staticmethod
    def _get_obs_by_id(obs_id: int) -> AbstractObservation:
        """
        :param obs_id: id of the observation
        :return:  object from the database identified by obs_id
        """
        return AbstractObservation.objects.filter(id=obs_id)[0]

    def _create_user_and_login(self):
        call_command("generate_admin_user")
        load_dotenv()
        admin_username = os.getenv("ADMIN_EMAIL")
        if not admin_username:
            self.fail("ADMIN_EMAIL environment variable not set")
        self.user = ObservatoryUser.objects.get(username=admin_username)
        self.client.force_login(self.user)

    @staticmethod
    def _day(d: int):
        return timezone.now().date() + timedelta(days=d)

    @staticmethod
    def _obs_exists_in_nextcloud(obs: AbstractObservation) -> bool:
        """
        Checks if observation exists in nextcloud. Works by trying to download the observation.

        :param obs: AbstractObservation to check whether it exists in nextcloud
        :return: True if Observation exists in nextcloud; else false
        """
        return nm.file_exists(generate_observation_path(obs))

    def test_calc_progress(self):
        # insert a specific Observation into the db and retrieve it as dict
        turmx = Observatory.objects.filter(name="TURMX")[0]
        self._create_imaging_observations(
            obs_id=1,
            target_name="I1",
            second_filter=True,
            observatory=turmx,
            frames_per_filter=100,
        )

        nm.initialize_connection()

        observation = AbstractObservation.objects.all()[0]
        serializer_class = get_serializer(observation.observation_type)
        serializer = serializer_class(observation)
        obs_dict = serializer.data

        progress1 = calc_progress(obs_dict)
        self.assertEqual(progress1, 0.0)  # initial progress is 0 (no images taken yet)

        obs_dict["targets"][0]["exposures"][0]["acceptedAmount"] = 50
        obs_dict["targets"][0]["exposures"][1]["acceptedAmount"] = 100
        progress2 = calc_progress(obs_dict)
        self.assertEqual(progress2, 75.0)

    def test_get_nextcloud_path(self):
        turmx = Observatory.objects.filter(name="TURMX")[0]
        self._create_imaging_observations(
            obs_id=42,
            target_name="I1",
            observatory=turmx,
        )
        path1 = f"{self.prefix}/TURMX/Projects/00042_Imaging_L_I1.json"

        observation = AbstractObservation.objects.all()[0]
        self.assertEqual(
            generate_observation_path(observation),
            path1,
        )

    def test_upload_from_db_simple(self):
        # fmt: off
        nm.initialize_connection()
        nm.mkdir(f"{self.prefix}/TURMX/Projects")
        nm.mkdir(f"{self.prefix}/TURMX2/Projects")
        turmx = Observatory.objects.filter(name="TURMX")[0]
        turmx2 = Observatory.objects.filter(name="TURMX2")[0]

        # insert test data
        self._create_imaging_observations(obs_id=0, target_name="I1", observatory=turmx)
        self._create_imaging_observations(obs_id=1, target_name="I2", observatory=turmx2)
        self._create_exoplanet_observation(obs_id=2, target_name="E1", observatory=turmx)
        self._create_exoplanet_observation(obs_id=3, target_name="E2", observatory=turmx2)
        self._create_variable_observation(obs_id=4, target_name="V1", observatory=turmx)
        self._create_variable_observation(obs_id=5, target_name="V2", observatory=turmx2)
        self._create_monitoring_observation(obs_id=6, target_name="M1", observatory=turmx)
        self._create_monitoring_observation(obs_id=7, target_name="M2", observatory=turmx2)
        self._create_expert_observation(obs_id=8, target_name="X1", observatory=turmx)
        self._create_expert_observation(obs_id=9, target_name="X2", observatory=turmx, project_status=ObservationStatus.COMPLETED)
        self._create_variable_observation(obs_id=10, target_name="V3", observatory=turmx, project_status=ObservationStatus.ERROR)
        self.assertEqual(11, AbstractObservation.objects.all().count())

        expected_uploads = [True, True, True, True, True, True, True, True, True, False, False]

        upload_observations()

        # check if correct files were uploaded and status set accordingly
        for i, should_be_uploaded in enumerate(expected_uploads):
            obs = self._get_obs_by_id(i)
            obs_is_uploaded = file_exists(generate_observation_path(obs))
            self.assertEqual(should_be_uploaded, obs_is_uploaded, f"For i={i}, obs={obs.id}")
            if obs_is_uploaded:
                self.assertEqual(obs.project_status, ObservationStatus.UPLOADED)
        self.assertEqual(self._get_obs_by_id(9).project_status, ObservationStatus.COMPLETED)
        self.assertEqual(self._get_obs_by_id(10).project_status, ObservationStatus.ERROR)

        nm.delete(self.prefix)
        # fmt: on

    def test_upload_from_db_status(self):
        nm.initialize_connection()
        nm.mkdir(f"{self.prefix}/TURMX/Projects")
        turmx = Observatory.objects.filter(name="TURMX")[0]

        # fmt: off
        # since the tested properties are inherited by ScheduledObservation, MonitoringObservation does not need to be tested manually
        self._create_expert_observation(obs_id=0, target_name="E0", observatory=turmx)
        self._create_expert_observation(obs_id=1, target_name="E1", start_scheduling=self._day(1), end_scheduling=self._day(2), observatory=turmx)
        self._create_expert_observation(obs_id=2, target_name="E2", start_scheduling=self._day(-2), end_scheduling=self._day(-3), observatory=turmx)
        self._create_imaging_observations(obs_id=3, target_name="I0", observatory=turmx)
        self._create_imaging_observations(obs_id=4, target_name="I1", project_status=ObservationStatus.COMPLETED, observatory=turmx)
        self._create_imaging_observations(obs_id=5, target_name="I2", project_status=ObservationStatus.ERROR, observatory=turmx)
        self.assertEqual(6, AbstractObservation.objects.all().count())

        # Expected values for day -1 to 4 (both included)
        status_e0 = [ObservationStatus.PENDING, ObservationStatus.UPLOADED, ObservationStatus.UPLOADED, ObservationStatus.UPLOADED]
        status_e1 = [ObservationStatus.PENDING, ObservationStatus.PENDING, ObservationStatus.UPLOADED, ObservationStatus.UPLOADED]
        status_e2 = [ObservationStatus.PENDING, ObservationStatus.PENDING, ObservationStatus.PENDING, ObservationStatus.PENDING]
        status_i0 = [ObservationStatus.UPLOADED, ObservationStatus.UPLOADED, ObservationStatus.UPLOADED, ObservationStatus.UPLOADED]
        status_i1 = [ObservationStatus.COMPLETED, ObservationStatus.COMPLETED, ObservationStatus.COMPLETED, ObservationStatus.COMPLETED]
        status_i2 = [ObservationStatus.ERROR, ObservationStatus.ERROR, ObservationStatus.ERROR, ObservationStatus.ERROR]
        expected_status = [status_e0, status_e1, status_e2, status_i0, status_i1, status_i2]

        for i in range(4):
            upload_observations(self._day(i-1))
            for j in range(len(expected_status)):
                obs = self._get_obs_by_id(j)
                expected_s = expected_status[j][i]
                actual_s = obs.project_status
                self.assertEqual(expected_s, actual_s, f"Day: {i-1} – Expected status: {expected_s}, actual: {actual_s} for obs {obs.id}",)

        # fmt: on
        nm.delete(self.prefix)

    def test_upload_from_db_repetitive_observations(self):
        # fmt: off
        nm.initialize_connection()
        nm.mkdir(f"{self.prefix}/TURMX/Projects")
        turmx = Observatory.objects.filter(name="TURMX")[0]

        self._create_expert_observation(obs_id=0, target_name="E0", start_scheduling=self._day(0), end_scheduling=self._day(5), cadence=1, observatory=turmx)
        self._create_expert_observation(obs_id=1, target_name="E1", start_scheduling=self._day(0), end_scheduling=self._day(7), cadence=2, observatory=turmx)
        self._create_monitoring_observation(obs_id=2, target_name="M0", start_scheduling=self._day(0), end_scheduling=self._day(7), cadence=3, observatory=turmx)
        self._create_monitoring_observation(obs_id=3, target_name="M1", start_scheduling=self._day(1), end_scheduling=self._day(3), cadence=1, project_status=ObservationStatus.UPLOADED, observatory=turmx)
        self._create_monitoring_observation(obs_id=4, target_name="M2", start_scheduling=self._day(2), end_scheduling=self._day(7), cadence=3, project_status=ObservationStatus.UPLOADED, observatory=turmx)
        self.assertEqual(5, AbstractObservation.objects.all().count())

        test_obs = [self._get_obs_by_id(i) for i in range(5)]

        # expected uploads of observations from day 0 to day 8 (both inclusive)
        expected_upload_e0 = [True, True, True, True, True, True, False, False, False]
        expected_upload_e1 = [True, False, True, False, True, False, True, False, False]
        expected_upload_m0 = [True, False, False, True, False, False, True, False, False]
        expected_upload_m1 = [False, True, True, True, False, False, False, False, False]
        expected_upload_m2 = [False, False, True, False, False, True, False, False, False]

        expected_uploads = [
            expected_upload_e0,
            expected_upload_e1,
            expected_upload_m0,
            expected_upload_m1,
            expected_upload_m2,
        ]

        # simulate day 0-8. Check if upload_status matches the one in the matrix
        for i in range(9):
            upload_observations(self._day(i))
            for j, obs in enumerate(test_obs):
                should_be_uploaded = expected_uploads[j][i]
                is_uploaded = self._obs_exists_in_nextcloud(obs)
                obs.target_name = obs.target.name
                self.assertEqual(
                    is_uploaded,
                    should_be_uploaded,
                    f"Day: {i} – Expected upload: {should_be_uploaded}, actual: {is_uploaded} for obs {obs.id}",
                )
                if is_uploaded:
                    nm.delete(generate_observation_path(obs))
                    # Setting next upload needs to be done manually in test. During deployment will be handled during NC download. For testing, it assumes that the observation during this night succeeded.
                    obs.next_upload += timedelta(days=obs.cadence)
                    obs.save()

        nm.delete(self.prefix)
        # fmt: on

    def test_download_non_scheduled(self):
        # fmt: off
        nm.initialize_connection()
        nm.mkdir(f"{self.prefix}/TURMX/Projects")
        turmx = Observatory.objects.filter(name="TURMX")[0]

        self._create_imaging_observations(obs_id=0, target_name="I1", observatory=turmx, frames_per_filter=10)
        self._create_exoplanet_observation(obs_id=1, target_name="E1", observatory=turmx)
        self._get_obs_by_id(1).filter_set.add(Filter.objects.get(filter_type=Filter.FilterType.HYDROGEN)) # add second filter to test multi filter handling

        self._create_variable_observation(obs_id=2, target_name="V1", observatory=turmx)

        upload_observations()

        # alter obs 0 to make it completed
        o0 = self._get_obs_by_id(0)
        o0_path = generate_observation_path(o0)
        o0_dict = nm.download_dict(o0_path)
        o0_dict["targets"][0]["exposures"][0]["acceptedAmount"] = 10
        nm.upload_dict(o0_path, o0_dict)
        # alter obs 1 to complete by half
        o1 = self._get_obs_by_id(1)
        o1_path = generate_observation_path(o1)
        o1_dict = nm.download_dict(o1_path)
        o1_dict["targets"][0]["exposures"][0]["acceptedAmount"] = 1000
        nm.upload_dict(o1_path, o1_dict)
        # no changes to obs 2

        update_observations()

        o0 = self._get_obs_by_id(0)
        self.assertFalse(self._obs_exists_in_nextcloud(o0))
        self.assertEqual(o0.project_status, ObservationStatus.COMPLETED)
        self.assertEqual(o0.project_completion, 100.0)
        o1 = self._get_obs_by_id(1)
        self.assertTrue(self._obs_exists_in_nextcloud(o1))
        self.assertEqual(o1.project_status, ObservationStatus.UPLOADED)
        self.assertEqual(o1.project_completion, 50.0)
        o2 = self._get_obs_by_id(2)
        self.assertTrue(self._obs_exists_in_nextcloud(o2))
        self.assertEqual(o2.project_status, ObservationStatus.UPLOADED)
        self.assertEqual(o2.project_completion, 0.0)

        # alter obs 1 to make it complete
        o1 = self._get_obs_by_id(1)
        o1_path = generate_observation_path(o1)
        o1_dict = nm.download_dict(o1_path)
        o1_dict["targets"][0]["exposures"][1]["acceptedAmount"] = 1000
        nm.upload_dict(o1_path, o1_dict)
        # alter obs 2 to make it complete by 99%
        o2 = self._get_obs_by_id(2)
        o2_path = generate_observation_path(o2)
        o2_dict = nm.download_dict(o2_path)
        o2_dict["targets"][0]["exposures"][0]["acceptedAmount"] = 99
        nm.upload_dict(o2_path, o2_dict)

        update_observations()

        o1 = self._get_obs_by_id(1)
        self.assertFalse(self._obs_exists_in_nextcloud(o1))
        self.assertEqual(o1.project_status, ObservationStatus.COMPLETED)
        self.assertEqual(o1.project_completion, 100.0)
        o2 = self._get_obs_by_id(2)
        self.assertTrue(self._obs_exists_in_nextcloud(o2))
        self.assertEqual(o2.project_status, ObservationStatus.UPLOADED)
        self.assertEqual(o2.project_completion, 99)

        # alter obs 2 to make it complete
        o2 = self._get_obs_by_id(2)
        o2_path = generate_observation_path(o2)
        o2_dict = nm.download_dict(o2_path)
        o2_dict["targets"][0]["exposures"][0]["acceptedAmount"] = 100
        nm.upload_dict(o2_path, o2_dict)

        update_observations()

        o2 = self._get_obs_by_id(2)
        self.assertFalse(self._obs_exists_in_nextcloud(o2))
        self.assertEqual(o2.project_status, ObservationStatus.COMPLETED)
        self.assertEqual(o2.project_completion, 100)

        nm.delete(self.prefix)
        # fmt: on

    def test_update_scheduled_1(self):
        """
        Simple test of a scheduled observation where to observation is uploaded every day. Every night, the entire partial observation is completed
        """

        # fmt: off
        nm.initialize_connection()
        nm.mkdir(f"{self.prefix}/TURMX/Projects")
        turmx = Observatory.objects.filter(name="TURMX")[0]

        self._create_monitoring_observation(obs_id=0, target_name="M0", start_scheduling=self._day(0), end_scheduling=self._day(5), cadence=1, observatory=turmx)

        for i in range(5):
            upload_observations(self._day(i))

            obs = self._get_obs_by_id(0)
            obs_path = generate_observation_path(obs)
            obs_dict = nm.download_dict(obs_path)

            obs_dict["targets"][0]["exposures"][0]["acceptedAmount"] = 10
            nm.upload_dict(obs_path, obs_dict)

            update_observations(self._day(i + 1))

            self.assertFalse(self._obs_exists_in_nextcloud(obs), f"i={i} and obs.id={obs.id}")
            self.assertEqual(self._get_obs_by_id(0).project_completion, ((i+1)/5)*100)


        self.assertEqual(self._get_obs_by_id(0).project_status, ObservationStatus.COMPLETED)

        nm.delete(self.prefix)
        # fmt: on

    def test_update_scheduled_2(self):
        """
        Simple test of a scheduled observation to test, that not finished but overdue observations are deleted correctly.
        """

        # fmt: off
        nm.initialize_connection()
        nm.mkdir(f"{self.prefix}/TURMX/Projects")
        turmx = Observatory.objects.filter(name="TURMX")[0]

        self._create_expert_observation(obs_id=0, target_name="E0", start_scheduling=self._day(0), end_scheduling=self._day(2), cadence=1, observatory=turmx, frames_per_filter=100)

        upload_observations()
        obs = self._get_obs_by_id(0)
        obs_path = generate_observation_path(obs)
        obs_dict = nm.download_dict(obs_path)
        obs_dict["targets"][0]["exposures"][0]["acceptedAmount"] = 42
        nm.upload_dict(obs_path, obs_dict)

        update_observations(self._day(1))
        obs = self._get_obs_by_id(0)
        self.assertTrue(self._obs_exists_in_nextcloud(obs))
        self.assertEqual(obs.project_completion, 50.0)
        self.assertEqual(obs.project_status, ObservationStatus.UPLOADED)

        update_observations(self._day(2))
        obs = self._get_obs_by_id(0)
        self.assertFalse(self._obs_exists_in_nextcloud(obs))
        self.assertEqual(obs.project_completion, 100.0) # <- although no pictures were taken, the completion is still set to 100
        self.assertEqual(obs.project_status, ObservationStatus.COMPLETED)

        nm.delete(self.prefix)
        # fmt: on

    def test_update_scheduled_3(self):
        """
        Complex test of a scheduled observation. Time interval of 10 days and cadence 3 but new upload is delayed.
        """

        # fmt: off
        nm.initialize_connection()
        nm.mkdir(f"{self.prefix}/TURMX/Projects")
        turmx = Observatory.objects.filter(name="TURMX")[0]

        self._create_expert_observation(obs_id=0, target_name="E0", start_scheduling=self._day(0), end_scheduling=self._day(10), cadence=3, observatory=turmx)

        # day 0/1
        upload_observations(self._day(0))
        obs = self._get_obs_by_id(0)
        obs_path = generate_observation_path(obs)
        obs_dict = nm.download_dict(obs_path)
        obs_dict["targets"][0]["exposures"][0]["acceptedAmount"] = 100
        nm.upload_dict(obs_path, obs_dict)
        update_observations(self._day(1))
        obs = self._get_obs_by_id(0)
        self.assertFalse(self._obs_exists_in_nextcloud(obs))
        self.assertEqual(obs.project_completion,10.0)
        self.assertEqual(obs.next_upload.day, self._day(3).day)
        self.assertEqual(obs.project_status, ObservationStatus.PENDING)

        # day 1/2
        upload_observations(self._day(1))
        update_observations(self._day(2))
        obs = self._get_obs_by_id(0)
        self.assertFalse(self._obs_exists_in_nextcloud(obs))
        self.assertEqual(obs.project_completion, 20.0)
        self.assertEqual(obs.next_upload.day, self._day(3).day)
        self.assertEqual(obs.project_status, ObservationStatus.PENDING)

        # day 2/3
        upload_observations(self._day(2))
        update_observations(self._day(3))
        obs = self._get_obs_by_id(0)
        self.assertFalse(self._obs_exists_in_nextcloud(obs))
        self.assertEqual(obs.project_completion, 30.0)
        self.assertEqual(obs.next_upload.day, self._day(3).day)
        self.assertEqual(obs.project_status, ObservationStatus.PENDING)

        # day 3/4
        upload_observations(self._day(3))
        update_observations(self._day(4))
        obs = self._get_obs_by_id(0)
        self.assertTrue(self._obs_exists_in_nextcloud(obs))
        self.assertEqual(obs.project_completion, 40.0)
        self.assertEqual(obs.next_upload.day, self._day(3).day)
        self.assertEqual(obs.project_status, ObservationStatus.UPLOADED)

        # day 4/5
        upload_observations(self._day(4))
        update_observations(self._day(5))
        obs = self._get_obs_by_id(0)
        self.assertTrue(self._obs_exists_in_nextcloud(obs))
        self.assertEqual(obs.project_completion, 50.0)
        self.assertEqual(obs.next_upload.day, self._day(3).day)
        self.assertEqual(obs.project_status, ObservationStatus.UPLOADED)

        # day 5/6
        upload_observations(self._day(5))
        obs = self._get_obs_by_id(0)
        obs_path = generate_observation_path(obs)
        obs_dict = nm.download_dict(obs_path)
        obs_dict["targets"][0]["exposures"][0]["acceptedAmount"] = 10
        nm.upload_dict(obs_path, obs_dict)
        update_observations(self._day(6))
        obs = self._get_obs_by_id(0)
        self.assertTrue(self._obs_exists_in_nextcloud(obs))
        self.assertEqual(obs.project_completion, 60.0)
        self.assertEqual(obs.next_upload.day, self._day(8).day)
        self.assertEqual(obs.project_status, ObservationStatus.UPLOADED)

        # day 6/7
        upload_observations(self._day(6))
        obs = self._get_obs_by_id(0)
        obs_path = generate_observation_path(obs)
        obs_dict = nm.download_dict(obs_path)
        obs_dict["targets"][0]["exposures"][0]["acceptedAmount"] = 20
        nm.upload_dict(obs_path, obs_dict)
        update_observations(self._day(7))
        obs = self._get_obs_by_id(0)
        self.assertTrue(self._obs_exists_in_nextcloud(obs))
        self.assertEqual(obs.project_completion, 70.0)
        self.assertEqual(obs.next_upload.day, self._day(8).day)
        self.assertEqual(obs.project_status, ObservationStatus.UPLOADED)

        # day 7/8
        upload_observations(self._day(7))
        obs = self._get_obs_by_id(0)
        obs_path = generate_observation_path(obs)
        obs_dict = nm.download_dict(obs_path)
        obs_dict["targets"][0]["exposures"][0]["acceptedAmount"] = 30
        nm.upload_dict(obs_path, obs_dict)
        update_observations(self._day(8))
        obs = self._get_obs_by_id(0)
        self.assertTrue(self._obs_exists_in_nextcloud(obs))
        self.assertEqual(obs.project_completion, 80.0)
        self.assertEqual(obs.next_upload.day, self._day(10).day)
        self.assertEqual(obs.project_status, ObservationStatus.UPLOADED)

        # day 8/9
        upload_observations(self._day(8))
        update_observations(self._day(9))
        obs = self._get_obs_by_id(0)
        self.assertTrue(self._obs_exists_in_nextcloud(obs))
        self.assertEqual(obs.project_completion, 90.0)
        self.assertEqual(obs.next_upload.day, self._day(10).day)
        self.assertEqual(obs.project_status, ObservationStatus.UPLOADED)

        # day 9/10
        upload_observations(self._day(9))
        obs = self._get_obs_by_id(0)
        obs_path = generate_observation_path(obs)
        obs_dict = nm.download_dict(obs_path)
        obs_dict["targets"][0]["exposures"][0]["acceptedAmount"] = 100
        nm.upload_dict(obs_path, obs_dict)
        update_observations(self._day(10))
        obs = self._get_obs_by_id(0)
        self.assertFalse(self._obs_exists_in_nextcloud(obs))
        self.assertEqual(obs.project_completion, 100.0)
        self.assertEqual(obs.next_upload.day, self._day(10).day) # although observation is finished, no new upload is set because it would be after the end of schedule
        self.assertEqual(obs.project_status, ObservationStatus.COMPLETED)

        nm.delete(self.prefix)
        # fmt: on

    def test_handling_non_existent_non_scheduled(self):
        """
        Checks for correct behavior when an observation does not exist in the nextcloud anymore.
        """

        # fmt: off
        nm.initialize_connection()
        nm.mkdir(f"{self.prefix}/TURMX/Projects")
        turmx = Observatory.objects.filter(name="TURMX")[0]

        self._create_imaging_observations(obs_id=0, observatory=turmx)
        self._create_imaging_observations(obs_id=1, observatory=turmx)

        upload_observations()
        self.assertEqual(2, len(AbstractObservation.objects.filter(project_status=ObservationStatus.UPLOADED)))

        nm.delete(generate_observation_path(self._get_obs_by_id(0)))

        obs = self._get_obs_by_id(1)
        obs_path = generate_observation_path(obs)
        obs_dict = nm.download_dict(obs_path)
        obs_dict["targets"][0]["exposures"][0]["acceptedAmount"] = 10
        nm.upload_dict(obs_path, obs_dict)

        update_observations()

        self.assertEqual(self._get_obs_by_id(0).project_status, ObservationStatus.ERROR)
        self.assertEqual(self._get_obs_by_id(1).project_status, ObservationStatus.COMPLETED)

        nm.delete(self.prefix)
        # fmt: on

    def test_handling_non_existent_scheduled(self):
        """
        Checks for correct behavior when an observation does not exist in the nextcloud anymore.
        """

        # fmt: off
        nm.initialize_connection()
        nm.mkdir(f"{self.prefix}/TURMX/Projects")
        turmx = Observatory.objects.filter(name="TURMX")[0]

        self._create_expert_observation(obs_id=0, target_name="E0", start_scheduling=self._day(0), end_scheduling=self._day(1), cadence=3, observatory=turmx)
        self._create_expert_observation(obs_id=1, target_name="E0", start_scheduling=self._day(0), end_scheduling=self._day(1), cadence=3, observatory=turmx)


        upload_observations()
        nm.delete(generate_observation_path(self._get_obs_by_id(0)))

        update_observations(self._day(1))
        self.assertEqual(self._get_obs_by_id(0).project_status, ObservationStatus.ERROR)
        self.assertEqual(self._get_obs_by_id(1).project_status, ObservationStatus.COMPLETED)

        nm.delete(self.prefix)

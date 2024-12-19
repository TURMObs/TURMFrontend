import filecmp
import json
import os
import unittest
from datetime import datetime, timedelta
from django.utils import timezone


import django
import django.test
from django.contrib.auth.models import User
from dotenv import load_dotenv
from nc_py_api import NextcloudException
from django.core.management import call_command
from numpy.ma.testutils import assert_equal

from nextcloud import nextcloud_manager as nm
from nextcloud.nextcloud_manager import file_exists, generate_observation_path
from nextcloud.nextcloud_sync import upload_observations, calc_progress
from observation_data.models import (
    AbstractObservation,
    ObservationType,
    ExoplanetObservation,
    MonitoringObservation,
    ImagingObservation,
    VariableObservation,
    CelestialTarget,
    Filter,
    Observatory,
    ExpertObservation,
    ObservationStatus,
)
from observation_data.serializers import get_serializer

file_upload = "nextcloud/test_data/upload_file.json"
file_download = "nextcloud/test_data/download_file.json"
file_nc = "file1.json"

dict_upload = "nextcloud/test_data/upload_dict.json"
dict_download = "nextcloud/test_data/download_dict.json"
dict_nc = "dict1.json"


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
    required_amount: int = 100,
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
        required_amount=required_amount,
    )

    obs.filter_set.add(Filter.objects.get(filter_type=Filter.FilterType.LUMINANCE))
    if second_filter:
        obs.filter_set.add(Filter.objects.get(filter_type=Filter.FilterType.BLUE))


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
    required_amount: int = 100,
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
        required_amount=required_amount,
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
    start_scheduling: datetime = timezone.now(),
    end_scheduling: datetime = (timezone.now() + timedelta(days=1)),
    frames_per_filter: int = 10,
    cadence: int = 1,
    required_amount: int = 100,
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
        frames_per_filter=frames_per_filter,
        cadence=cadence,
        required_amount=required_amount,
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
    start_scheduling: datetime = timezone.now(),
    end_scheduling: datetime = (timezone.now() + timedelta(days=1)),
    frames_per_filter: int = 10,
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
    required_amount: int = 100,
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
        frames_per_filter=frames_per_filter,
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
        required_amount=required_amount,
    )

    obs.filter_set.add(Filter.objects.get(filter_type=Filter.FilterType.LUMINANCE))


def _obs_exists_in_nextcloud(obs: AbstractObservation) -> bool:
    """
    Checks if observation exists in nextcloud. Works by trying to download the observation.

    :param obs: AbstractObservation to check whether it exists in nextcloud
    :return True if Observation exists in nextcloud; else false
    """
    return nm.file_exists(generate_observation_path(obs))


def _get_obs_by_id(obs_id: int) -> AbstractObservation:
    """
    :param obs_id: id of the observation
    :return the observation object from the database identified by obs_id
    """
    return AbstractObservation.objects.filter(id=obs_id)[0]


def _create_user_and_login(test_instance):
    call_command("generate_admin_user")
    load_dotenv()
    admin_username = os.getenv("ADMIN_EMAIL")
    if not admin_username:
        test_instance.fail("ADMIN_EMAIL environment variable not set")
    test_instance.user = User.objects.get(username=admin_username)
    test_instance.client.force_login(test_instance.user)


def _day(d: int):
    return timezone.now() + timedelta(days=d)


@unittest.skip("Skip in CI until solution for nc-container in found")
class NextcloudManagerTestCaseWithoutInit(django.test.TestCase):
    def test_access_nc_without_init(self):
        self.client = django.test.Client()
        with self.assertRaises(Exception):
            nm.delete("/does/not/matter")


# noinspection DuplicatedCode
@unittest.skip("Skip in CI until solution for nc-container in found")
class NextcloudManagerTestCase(django.test.TestCase):
    def setUp(self):
        nm.initialize_connection()

        self.LOCAL_PATH = "test_data"

        self.maxDiff = None
        self.client = django.test.Client()
        self.user = None
        _create_user_and_login(self)

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
        try:
            path = "this/is/a/long/path/"
            nm.mkdir("this/is/test")
            nm.mkdir(path)
            nm.upload_file(path + file_nc, file_upload)
            nm.delete("this")
        except Exception:
            self.assertRaises(NextcloudException)

    def test_file_exists(self):
        nm.mkdir("Test/file/exists")
        nm.upload_file("Test/file/exists/test.json", file_upload)
        self.assertTrue(file_exists("Test/file/exists/test.json"))
        self.assertFalse(file_exists("Test/file/exists/test_again.json"))
        self.assertFalse(file_exists("Test/file"))
        nm.delete("Test")


@unittest.skip("Skip in CI until solution for nc-container in found")
class NextcloudSyncTestCase(django.test.TestCase):
    def setUp(self):
        nm.initialize_connection()
        call_command("populate_observatories")

        self.LOCAL_PATH = "test_data"

        self.maxDiff = None
        self.client = django.test.Client()
        self.user = None
        _create_user_and_login(self)

    def test_calc_progress(self):
        # insert a specific Observation into the db and retrieve it as dict
        turmx = Observatory.objects.filter(name="TURMX")[0]
        _create_imaging_observations(
            self,
            obs_id=1,
            target_name="I1",
            required_amount=100,
            second_filter=True,
            observatory=turmx,
        )
        observation = AbstractObservation.objects.all()[0]
        serializer_class = get_serializer(observation.observation_type)
        serializer = serializer_class(observation)
        obs_dict = serializer.data

        nm.initialize_connection()
        nm.upload_dict("test.json", obs_dict)

        progress1 = calc_progress(obs_dict)
        self.assertEqual(progress1, 0)  # initial progress is 0 (no images taken yet)

        obs_dict["targets"][0]["exposures"][0]["acceptedAmount"] = 50
        obs_dict["targets"][0]["exposures"][1]["acceptedAmount"] = 100
        progress2 = calc_progress(obs_dict)
        self.assertEqual(progress2, 0.75)

        nm.delete("test.json")

    def test_get_nextcloud_path(self):
        turmx = Observatory.objects.filter(name="TURMX")[0]
        _create_imaging_observations(
            self, obs_id=42, target_name="I1", required_amount=100, observatory=turmx
        )
        observation = AbstractObservation.objects.all()[0]
        self.assertEqual(
            generate_observation_path(observation),
            "TURMX/Projects/00042_Imaging_L_I1.json",
        )

    def test_upload_from_db_simple(self):
        # fmt: off
        nm.initialize_connection()
        nm.mkdir("TURMX/Projects")
        nm.mkdir("TURMX2/Projects")
        turmx = Observatory.objects.filter(name="TURMX")[0]
        turmx2 = Observatory.objects.filter(name="TURMX2")[0]



        # insert test data
        _create_imaging_observations(self, obs_id=0, target_name="I1", observatory=turmx)
        _create_imaging_observations(self, obs_id=1, target_name="I2", observatory=turmx2)
        _create_exoplanet_observation(self, obs_id=2, target_name="E1", observatory=turmx)
        _create_exoplanet_observation(self, obs_id=3, target_name="E2", observatory=turmx2)
        _create_variable_observation(self, obs_id=4, target_name="V1", observatory=turmx)
        _create_variable_observation(self, obs_id=5, target_name="V2", observatory=turmx2)
        _create_monitoring_observation(self, obs_id=6, target_name="M1", observatory=turmx)
        _create_monitoring_observation(self, obs_id=7, target_name="M2", observatory=turmx2)
        _create_expert_observation(self, obs_id=8, target_name="X1", observatory=turmx)
        _create_expert_observation(self, obs_id=9, target_name="X2", observatory=turmx2, project_status=ObservationStatus.COMPLETED)
        _create_variable_observation(self, obs_id=10, target_name="V3", observatory=turmx2, project_status=ObservationStatus.ERROR)
        self.assertEqual(11, AbstractObservation.objects.all().count())

        expected_uploads = [True, True, True, True, True, True, True, True, True, False, False]

        upload_observations()

        # check if correct files were uploaded and status set accordingly
        for i, should_be_uploaded in enumerate(expected_uploads):
            obs = _get_obs_by_id(i)
            obs_is_uploaded = file_exists(generate_observation_path(obs))
            self.assertEqual(should_be_uploaded, obs_is_uploaded)
            if obs_is_uploaded:
                assert_equal(obs.project_status, ObservationStatus.UPLOADED)
        assert_equal(_get_obs_by_id(9).project_status, ObservationStatus.COMPLETED)
        assert_equal(_get_obs_by_id(10).project_status, ObservationStatus.ERROR)

        nm.delete("TURMX")
        nm.delete("TURMX2")
        # fmt: on

    def test_upload_from_db_status(self):
        nm.initialize_connection()
        nm.mkdir("TURMX/Projects")
        nm.mkdir("TURMX2/Projects")
        turmx = Observatory.objects.filter(name="TURMX")[0]

        # fmt: off
        # since the tested properties are inherited by ScheduledObservation, MonitoringObservation does not need to be tested manually
        _create_expert_observation(self, obs_id=0, target_name="E0", observatory=turmx)
        _create_expert_observation(self, obs_id=1, target_name="E1", start_scheduling=_day(1), end_scheduling=_day(2), observatory=turmx)
        _create_expert_observation(self, obs_id=2, target_name="E2", start_scheduling=_day(-2), end_scheduling=_day(-3), observatory=turmx)
        _create_imaging_observations(self, obs_id=3, target_name="I0", observatory=turmx)
        _create_imaging_observations(self, obs_id=4, target_name="I1", project_status=ObservationStatus.COMPLETED, observatory=turmx)
        _create_imaging_observations(self, obs_id=5, target_name="I2", project_status=ObservationStatus.ERROR, observatory=turmx)
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
            upload_observations(_day(i-1))
            for j in range(len(expected_status)):
                obs = _get_obs_by_id(j)
                expected_s = expected_status[j][i]
                actual_s = obs.project_status
                self.assertEqual(expected_s, actual_s, f"Day: {i-1} – Expected status: {expected_s}, actual: {actual_s} for obs {obs.id}",)

        # fmt: on
        nm.delete("TURMX")
        nm.delete("TURMX2")

    def test_upload_from_db_repetitive_observations(self):
        # fmt: off
        nm.initialize_connection()
        nm.mkdir("TURMX/Projects")
        nm.mkdir("TURMX2/Projects")
        turmx = Observatory.objects.filter(name="TURMX")[0]

        _create_expert_observation(self, obs_id=0, target_name="E0", start_scheduling=_day(0), end_scheduling=_day(5), cadence=1, observatory=turmx)
        _create_expert_observation(self, obs_id=1, target_name="E1", start_scheduling=_day(0), end_scheduling=_day(7), cadence=2, observatory=turmx)
        _create_monitoring_observation(self, obs_id=2, target_name="M0", start_scheduling=_day(0), end_scheduling=_day(7), cadence=3, observatory=turmx)
        _create_monitoring_observation(self, obs_id=3, target_name="M1", start_scheduling=_day(1), end_scheduling=_day(3), cadence=1, project_status=ObservationStatus.UPLOADED, observatory=turmx)
        _create_monitoring_observation(self, obs_id=4, target_name="M2", start_scheduling=_day(2), end_scheduling=_day(7), cadence=3, project_status=ObservationStatus.UPLOADED, observatory=turmx)
        assert_equal(5, AbstractObservation.objects.all().count())

        test_obs = [_get_obs_by_id(i) for i in range(5)]

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
            upload_observations(_day(i))
            for j, obs in enumerate(test_obs):
                should_be_uploaded = expected_uploads[j][i]
                is_uploaded = _obs_exists_in_nextcloud(obs)
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

        nm.mkdir("TURMX")
        nm.mkdir("TURMX2")
        # fmt: on

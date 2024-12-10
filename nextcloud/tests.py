import filecmp
import json
import unittest
import django
import django.test
from django.contrib.auth.models import User
from nc_py_api import NextcloudException
from django.core.management import call_command
from numpy.ma.testutils import assert_equal

from nextcloud import nextcloud_manager as nm
from nextcloud.nextcloud_sync import (
    upload_observations,
    calc_progress,
    get_nextcloud_path,
)
from observation_data.models import (
    AbstractObservation,
    ObservationStatus,
    ObservationType,
    ExoplanetObservation,
    MonitoringObservation,
    ImagingObservation,
    VariableObservation,
    CelestialTarget,
    Filter,
    Observatory,
    ExpertObservation,
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
    observatory: Observatory = Observatory.objects.all()[0],
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
    observatory: Observatory = Observatory.objects.all()[0],
    target_name: str = "TestTargetExoplanet",
    target_ra: str = "0",
    target_dec: str = "0",
    project_status: ObservationStatus = ObservationStatus.PENDING,
    project_completion: float = 0.0,
    priority: int = 1,
    exposure_time: float = 10.0,
    start_observation: datetime = (timezone.now() - timedelta(seconds=1)),
    end_observation: datetime = (
        timezone.now() + timedelta(days=1) - timedelta(seconds=1)
    ),
):
    """
    Creates exoplanet observations from scratch without checks from serializers. Sets today as start and tomorrow as default start/end times.
    """
    target = CelestialTarget.objects.create(
        name=target_name, ra=target_ra, dec=target_dec
    )

    obs = ExoplanetObservation.objects.create(
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
    observatory: Observatory = Observatory.objects.all()[0],
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
    observatory: Observatory = Observatory.objects.all()[0],
    target_name: str = "TestTargetMonitoring",
    target_ra: str = "0",
    target_dec: str = "0",
    project_status: ObservationStatus = ObservationStatus.PENDING,
    project_completion: float = 0.0,
    priority: int = 1,
    exposure_time: float = 10.0,
    start_scheduling: datetime = (timezone.now() - timedelta(seconds=1)),
    end_scheduling: datetime = (
        timezone.now() + timedelta(days=1) - timedelta(seconds=1)
    ),
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
        frames_per_filter=frames_per_filter,
        cadence=cadence,
        required_amount=required_amount,
    )

    obs.filter_set.add(Filter.objects.get(filter_type=Filter.FilterType.LUMINANCE))


def _create_expert_observation(
    self,
    observatory: Observatory = Observatory.objects.all()[0],
    target_name: str = "TestTargetExpert",
    target_ra: str = "0",
    target_dec: str = "0",
    project_status: ObservationStatus = ObservationStatus.PENDING,
    project_completion: float = 0.0,
    priority: int = 1,
    exposure_time: float = 10.0,
    start_scheduling: datetime = (timezone.now() - timedelta(seconds=1)),
    end_scheduling: datetime = (
        timezone.now() + timedelta(days=1) - timedelta(seconds=1)
    ),
    frames_per_filter: int = 10,
    dither_every: float = 10.0,
    binning: str = "auto",
    gain: int = 10,
    offset: float = 10,
    start_observation: datetime = (timezone.now() - timedelta(seconds=1)),
    end_observation: datetime = (
        timezone.now() + timedelta(days=1) - timedelta(seconds=1)
    ),
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


def _create_user_and_login(test_instance):
    call_command("generate_admin_user")
    load_dotenv()
    admin_username = os.getenv("ADMIN_EMAIL")
    if not admin_username:
        test_instance.fail("ADMIN_EMAIL environment variable not set")
    test_instance.user = User.objects.get(username=admin_username)
    test_instance.client.force_login(test_instance.user)


class NextcloudManagerTestCaseWithoutInit(django.test.TestCase):
    def test_access_nc_without_init(self):
        self.client = django.test.Client()
        with self.assertRaises(Exception):
            nm.delete("/does/not/matter")


# noinspection DuplicatedCode
class NextcloudManagerTestCase(django.test.TestCase):
    def setUp(self):
        nm.initialize_connection()

        self.LOCAL_PATH = "test_data"

        self.maxDiff = None
        self.client = django.test.Client()
        self.user = None
        _create_user_and_login(self)

        nm._delete_all()

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
            nm.upload_file("non/existing/path" + file_nc, file_upload)

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
            nm.upload_file(
                "mkdir_test/mkdir_test.json", file_upload
            )  # throws error if directory does not exist
            nm.delete("mkdir_test")
        except Exception:
            self.assertRaises(NextcloudException)

    def test_mkdir_complex(self):
        try:
            path = "this/is/a/long/path/"
            nm.mkdir("this/is/test")
            nm.mkdir(path)
            nm.upload_file(path + file_nc, file_upload)
            nm.delete("this")
        except Exception:
            self.assertRaises(NextcloudException)


class NextcloudSyncTestCase(django.test.TestCase):
    def setUp(self):
        nm.initialize_connection()
        call_command("populate_observatories")

        self.LOCAL_PATH = "test_data"

        self.maxDiff = None
        self.client = django.test.Client()
        self.user = None
        _create_user_and_login(self)

        nm._delete_all()

    def test_upload_from_db_simple(self):
        nm._delete_all()
        nm.mkdir("TURMX/Projects")
        nm.mkdir("TURMX2/Projects")
        turmx2 = Observatory.objects.all()[1]
        nm.initialize_connection()

        # insert test data
        _create_imaging_observations(self, target_name="I1")
        _create_imaging_observations(self, target_name="I2", observatory=turmx2)
        _create_exoplanet_observation(self, target_name="E1")
        _create_exoplanet_observation(self, target_name="E2", observatory=turmx2)
        _create_variable_observation(self, target_name="V1")
        _create_variable_observation(self, target_name="V2", observatory=turmx2)
        _create_monitoring_observation(self, target_name="M1")
        _create_monitoring_observation(self, target_name="M2", observatory=turmx2)
        _create_expert_observation(self, target_name="X1")
        _create_expert_observation(self, target_name="X2", observatory=turmx2)

        _create_expert_observation(
            self,
            target_name="X3",
            observatory=turmx2,
            project_status=ObservationStatus.COMPLETED,
        )
        _create_variable_observation(
            self,
            target_name="V3",
            observatory=turmx2,
            project_status=ObservationStatus.ERROR,
        )

        # upload observation
        upload_observations()

        # completed files should not exist in the nextcloud
        observations_not_pending = AbstractObservation.objects.filter(
            project_status=ObservationStatus.COMPLETED
        )
        for obs in observations_not_pending:
            with self.assertRaises(Exception):
                nm.delete(get_nextcloud_path(obs))

        # all files with status upload pending should exist in the nc
        observations_pending = AbstractObservation.objects.filter(
            project_status=ObservationStatus.PENDING
        )
        for obs in observations_pending:
            try:
                nm.delete(
                    get_nextcloud_path(obs)
                )  # raises an exception when file does not exist
            except Exception:
                self.fail("Unexpected exception when deleting {}".format(obs))

        nm.delete("TURMX")
        nm.delete("TURMX2")

    def test_upload_from_db_complex(self):
        # todo write tests that test the behavior of scheduled observations
        pass

    def test_calc_progress(self):
        # insert a specific Observation into the db and retrieve it as dict
        _create_imaging_observations(
            self, target_name="I1", required_amount=100, second_filter=True
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
        nm.upload_dict("test.json", obs_dict)
        self.assertEqual(progress2, 0.75)
        nm._delete_all()

    def test_get_nextcloud_path(self):
        _create_imaging_observations(self, target_name="I1", required_amount=100)
        observation = AbstractObservation.objects.all()[0]
        assert_equal(
            get_nextcloud_path(observation), "TURMX/Projects/00001_Imaging_L_I1.json"
        )

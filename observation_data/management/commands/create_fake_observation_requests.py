from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from observation_data.models import (
    AbstractObservation,
    ExoplanetObservation,
    ObservationType,
    Observatory,
    CelestialTarget,
    Filter,
)
import os
from datetime import timedelta
import datetime


class Command(BaseCommand):
    help = "Inserts fake observation requests into the database"

    def handle(self, *args, **options):
        email = os.environ.get("ADMIN_EMAIL")
        user = User.objects.get(email=email)

        # Get or create an observatory
        observatory, _ = Observatory.objects.get_or_create(name="TURMX")

        self._create_exoplanet_observation(user, observatory)

    def _create_exoplanet_observation(
        self,
        user,
        observatory: Observatory = Observatory.objects.all()[0],
        target_name: str = "TestTargetExoplanet",
        target_ra: str = "0",
        target_dec: str = "0",
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
            user=user,
            created_at=timezone.now(),
            observation_type=ObservationType.EXOPLANET,
            project_status=AbstractObservation.ObservationStatus.PENDING,
            project_completion=project_completion,
            priority=priority,
            exposure_time=exposure_time,
            start_observation=start_observation,
            end_observation=end_observation,
        )

        obs.filter_set.add(Filter.objects.get(filter_type=Filter.FilterType.LUMINANCE))

        obs.save()

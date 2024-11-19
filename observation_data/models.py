"""
All database models for the observation requests, targets and observatories.
"""

from django.contrib.auth.models import User
from django.db import models


class CelestialTarget(models.Model):
    """
    Model for the celestial targets that can be observed.
    """

    catalog_id = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    ra = models.CharField(max_length=25)
    dec = models.CharField(max_length=25)


class Observatory(models.Model):
    """
    Model for the observatories that can be used for the observations.
    """

    name = models.CharField(max_length=100, primary_key=True)
    horizon_offset = models.DecimalField(max_digits=5, decimal_places=2)
    min_stars = models.IntegerField()
    max_HFR = models.DecimalField(max_digits=5, decimal_places=2)
    max_guide_error = models.DecimalField(max_digits=15, decimal_places=2)
    filter_set = models.CharField(max_length=100)  # comma separated list of filters


class AbstractObservation(models.Model):
    """
    Abstract class for the different types of observations including common fields.
    Note that this means that each observation will have a corresponding row in the AbstractObservation table.
    """

    class ObservationType(models.TextChoices):
        IMAGING = "Imaging"
        EXOPLANET = "Exoplanet"
        VARIABLE = "Variable"
        MONITORING = "Monitoring"
        EXPERT = "Expert"

    class ObservationStatus(models.TextChoices):
        PENDING = "Pending Upload"
        UPLOADED = "Uploaded"
        ERROR = "Error"
        COMPLETED = "Completed"

    observatory = models.ForeignKey(
        Observatory,
        on_delete=models.PROTECT,
        related_name="+",  # prevents backward relation
        db_column="observatory",
    )
    target = models.ForeignKey(
        CelestialTarget,
        on_delete=models.PROTECT,
        related_name="+",  # prevents backward relation
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField()
    observation_type = models.CharField(
        choices=ObservationType.choices, db_column="type"
    )
    project_status = models.CharField(choices=ObservationStatus.choices)
    project_completion = models.DecimalField(max_digits=5, decimal_places=2)
    priority = models.IntegerField()
    exposure_time = models.DecimalField(max_digits=10, decimal_places=2)
    filter_set = models.CharField(max_length=100)  # comma separated list of filters


class ImagingObservation(AbstractObservation):
    frames_per_filter = models.IntegerField()


class ExoplanetObservation(AbstractObservation):
    start_observation = models.DateTimeField()
    end_observation = models.DateTimeField()


class VariableObservation(AbstractObservation):
    minimum_altitude = models.DecimalField(max_digits=5, decimal_places=2)


class MonitoringObservation(AbstractObservation):
    frames_per_filter = models.IntegerField()
    start_scheduling = models.DateTimeField()
    end_scheduling = models.DateTimeField()
    cadence = models.DurationField()


class ExpertObservation(AbstractObservation):
    frames_per_filter = models.IntegerField()
    dither_every = models.DecimalField(max_digits=5, decimal_places=2)
    binning = models.CharField(max_length=50)
    subframe = models.CharField(max_length=50)
    gain = models.IntegerField()
    offset = models.IntegerField()
    start_observation = models.DateTimeField()
    end_observation = models.DateTimeField()
    start_scheduling = models.DateTimeField()
    end_scheduling = models.DateTimeField()
    cadence = models.DurationField()
    moon_separation_angle = models.DecimalField(max_digits=5, decimal_places=2)
    moon_separation_width = models.IntegerField()
    minimum_altitude = models.DecimalField(max_digits=5, decimal_places=2)
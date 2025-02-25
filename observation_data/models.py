"""
All database models for the observation requests, targets and observatories.
"""

from django.core.validators import RegexValidator
from django.db import models
from polymorphic.models import PolymorphicModel

from TURMFrontend import settings


class ObservationType(models.TextChoices):
    IMAGING = "Imaging"
    EXOPLANET = "Exoplanet"
    VARIABLE = "Variable"
    MONITORING = "Monitor"
    EXPERT = "Expert"


class ObservationStatus(models.TextChoices):
    PENDING = "Pending Upload"
    UPLOADED = "Uploaded"
    ERROR = "Error"
    COMPLETED = "Completed"
    PENDING_DELETION = "Pending Deletion"


class CelestialTarget(models.Model):
    """
    Model for the celestial targets that can be observed.
    """

    name = models.CharField(
        max_length=100,
        validators=[RegexValidator(r"^\S*$", message="No spaces allowed")],
    )
    catalog_id = models.CharField(
        max_length=100,
        blank=True,
        validators=[RegexValidator(r"^\S*$", message="No spaces allowed")],
    )
    ra = models.CharField(max_length=25)
    dec = models.CharField(max_length=25)


class ExposureSettings(models.Model):
    """
    Model for the exposure settings that can be used for the observations.
    """

    gain = models.IntegerField()
    offset = models.IntegerField()
    binning = models.IntegerField()
    subframe = models.DecimalField(max_digits=5, decimal_places=4)


class Filter(models.Model):
    """
    Model for the filters that can be used for the observations.
    """

    filter_type = models.CharField(db_column="type", max_length=6, primary_key=True)
    moon_separation_angle = models.DecimalField(max_digits=5, decimal_places=2)
    moon_separation_width = models.IntegerField()

    def __str__(self):
        return self.filter_type


class Observatory(models.Model):
    """
    Model for the observatories that can be used for the observations.
    """

    name = models.CharField(max_length=100, primary_key=True)
    horizon_offset = models.DecimalField(max_digits=5, decimal_places=2)
    min_stars = models.IntegerField()
    max_HFR = models.DecimalField(max_digits=5, decimal_places=2)
    max_guide_error = models.DecimalField(max_digits=15, decimal_places=2)
    filter_set = models.ManyToManyField(Filter, related_name="observatories")
    exposure_settings = models.ManyToManyField(
        ExposureSettings,
        through="ObservatoryExposureSettings",
        related_name="observatories",
    )

    def __str__(self):
        return self.name


class ObservatoryExposureSettings(models.Model):
    """
    Model for the many-to-many relationship between observatories and exposure settings.
    """

    observatory = models.ForeignKey(
        Observatory, on_delete=models.CASCADE, db_column="observatory"
    )
    exposure_settings = models.ForeignKey(ExposureSettings, on_delete=models.CASCADE)
    observation_type = models.CharField(choices=ObservationType, db_column="type")


class AbstractObservation(PolymorphicModel):
    """
    Abstract class for the different types of observations including common fields.
    Note that this means that each observation will have a corresponding row in the AbstractObservation table.
    """

    observatory = models.ForeignKey(
        Observatory,
        on_delete=models.SET_NULL,
        related_name="+",  # prevents backward relation
        db_column="observatory",
        null=True,
    )
    target = models.ForeignKey(
        CelestialTarget,
        on_delete=models.PROTECT,
        related_name="+",  # prevents backward relation
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField()
    observation_type = models.CharField(choices=ObservationType, db_column="type")
    project_status = models.CharField(choices=ObservationStatus)
    project_completion = models.DecimalField(max_digits=5, decimal_places=2)
    priority = models.IntegerField()
    exposure_time = models.DecimalField(max_digits=10, decimal_places=2)
    filter_set = models.ManyToManyField(Filter, related_name="observations")


class ImagingObservation(AbstractObservation):
    frames_per_filter = models.IntegerField()


class ExoplanetObservation(AbstractObservation):
    start_observation = models.DateTimeField()
    end_observation = models.DateTimeField()


class VariableObservation(AbstractObservation):
    minimum_altitude = models.DecimalField(max_digits=5, decimal_places=2)
    frames_per_filter = models.IntegerField()


class ScheduledObservation(AbstractObservation):
    class Meta:
        abstract = True

    start_scheduling = models.DateField(blank=True, null=True)
    end_scheduling = models.DateField(blank=True, null=True)
    next_upload = models.DateField(blank=True, null=True)
    cadence = models.IntegerField(blank=True, null=True)


class MonitoringObservation(ScheduledObservation):
    minimum_altitude = models.DecimalField(max_digits=5, decimal_places=2)
    frames_per_filter = models.IntegerField()


class ExpertObservation(ScheduledObservation):
    frames_per_filter = models.IntegerField()
    dither_every = models.IntegerField()
    binning = models.IntegerField()
    subframe = models.DecimalField(max_digits=5, decimal_places=4)
    gain = models.IntegerField()
    offset = models.IntegerField()
    start_observation = models.DateTimeField(blank=True, null=True)
    end_observation = models.DateTimeField(blank=True, null=True)
    start_observation_time = models.TimeField(blank=True, null=True)
    end_observation_time = models.TimeField(blank=True, null=True)
    moon_separation_angle = models.DecimalField(max_digits=5, decimal_places=2)
    moon_separation_width = models.IntegerField()
    minimum_altitude = models.DecimalField(max_digits=5, decimal_places=2)


class DefaultRequestSettings(models.Model):
    """
    Model for default values for observation requests.
    """

    id = models.IntegerField(primary_key=True, default=0)
    settings = models.JSONField(default=dict)

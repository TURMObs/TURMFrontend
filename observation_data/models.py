"""
All database models for the observation requests, targets and observatories.
"""

from django.contrib.auth.models import User
from django.db import models


class ObservationType(models.TextChoices):
    IMAGING = "Imaging"
    EXOPLANET = "Exoplanet"
    VARIABLE = "Variable"
    MONITORING = "Monitor"
    EXPERT = "Expert"


class CelestialTarget(models.Model):
    """
    Model for the celestial targets that can be observed.
    """

    name = models.CharField(max_length=100)
    ra = models.CharField(max_length=25)
    dec = models.CharField(max_length=25)


class ExposureSettings(models.Model):
    """
    Model for the exposure settings that can be used for the observations.
    """

    gain = models.IntegerField()
    offset = models.IntegerField()
    binning = models.IntegerField()
    subFrame = models.DecimalField(max_digits=10, decimal_places=4)


class Filter(models.Model):
    """
    Model for the filters that can be used for the observations.
    """

    class FilterType(models.TextChoices):
        # todo check naming
        LUMINANCE = "L"
        RED = "R"
        GREEN = "G"
        BLUE = "B"
        HYDROGEN = "H"
        OXYGEN = "O"
        SULFUR = "S"
        SR = "SR"
        SG = "SG"
        SI = "SI"

    filter_type = models.CharField(
        choices=FilterType.choices, db_column="type", max_length=2, primary_key=True
    )
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
        Observatory, on_delete=models.DO_NOTHING, db_column="observatory"
    )
    exposure_settings = models.ForeignKey(ExposureSettings, on_delete=models.DO_NOTHING)
    observation_type = models.CharField(
        choices=ObservationType.choices, db_column="type"
    )


class AbstractObservation(models.Model):
    """
    Abstract class for the different types of observations including common fields.
    Note that this means that each observation will have a corresponding row in the AbstractObservation table.
    """

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
    filter_set = models.ManyToManyField(Filter, related_name="observations")


class ImagingObservation(AbstractObservation):
    frames_per_filter = models.IntegerField()
    required_amount = models.IntegerField()


class ExoplanetObservation(AbstractObservation):
    start_observation = models.DateTimeField()
    end_observation = models.DateTimeField()


class VariableObservation(AbstractObservation):
    minimum_altitude = models.DecimalField(max_digits=5, decimal_places=2)
    required_amount = models.IntegerField()


class MonitoringObservation(AbstractObservation):
    frames_per_filter = models.IntegerField()
    start_scheduling = models.DateTimeField()
    end_scheduling = models.DateTimeField()
    cadence = models.IntegerField()
    required_amount = models.IntegerField()


class ExpertObservation(AbstractObservation):
    frames_per_filter = models.IntegerField()
    dither_every = models.DecimalField(max_digits=5, decimal_places=2)
    binning = models.CharField(max_length=50)
    gain = models.IntegerField()
    offset = models.IntegerField()
    start_observation = models.DateTimeField()
    end_observation = models.DateTimeField()
    start_scheduling = models.DateTimeField()
    end_scheduling = models.DateTimeField()
    cadence = models.IntegerField()
    moon_separation_angle = models.DecimalField(max_digits=5, decimal_places=2)
    moon_separation_width = models.IntegerField()
    minimum_altitude = models.DecimalField(max_digits=5, decimal_places=2)
    required_amount = models.IntegerField()

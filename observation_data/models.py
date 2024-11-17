from django.db import models

# Create your models here.


class CelestialTarget(models.Model):
    name = models.CharField(max_length=100)
    coordinates = models.CharField(max_length=100)


class AbstractObservation(models.Model):
    observatory = models.CharField(max_length=100)
    target = models.ForeignKey(
        CelestialTarget, on_delete=models.DO_NOTHING, related_name="observation_data"
    )


class ExoplanetObservation(AbstractObservation):
    filter_set = models.CharField(max_length=100)

"""
Serializers for the observation_data app models.
For a usage example, see the create_observation view in the views.py file.
"""

from rest_framework import serializers

from .models import (
    CelestialTarget,
    ImagingObservation,
    ExoplanetObservation,
    VariableObservation,
    MonitoringObservation,
    ExpertObservation,
    Observatory,
)

priorities = {
    "Imaging": 10,
    "Exoplanet": 1000000,
    "Variable": 100000,
    "Monitoring": 1000,
}

base_fields = [
    "observatory",
    "target",
    "user",
    "observation_type",
    "exposure_time",
    "filter_set",
]


def _create_observation(validated_data, observation_type, model):
    """
    Create an instance of an observation model.
    :param validated_data: Data to create the observation
    :param observation_type: Type of observation
    :param model: Model to create
    :return: Created observation

    """
    target_data = validated_data.pop("target")
    target_catalog_id = target_data.get("catalog_id")
    created_target, created = CelestialTarget.objects.get_or_create(
        catalog_id=target_catalog_id,
        name=target_data.get("name"),
        ra=target_data.get("ra"),
        dec=target_data.get("dec"),
    )

    validated_data["project_status"] = "Pending Upload"
    if observation_type in priorities:
        validated_data["priority"] = priorities[observation_type]

    observation = model.objects.create(target=created_target, **validated_data)
    return observation


class CelestialTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CelestialTarget
        fields = ["catalog_id", "name", "ra", "dec"]


class ObservatorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Observatory
        fields = [
            "name",
            "horizon_offset",
            "min_stars",
            "max_HFR",
            "max_guide_error",
            "filter_set",
        ]


class ImagingObservationSerializer(serializers.ModelSerializer):
    target = CelestialTargetSerializer()

    class Meta:
        model = ImagingObservation
        fields = base_fields + ["frames_per_filter"]

    def create(self, validated_data):
        return _create_observation(validated_data, "Imaging", ImagingObservation)


class ExoplanetObservationSerializer(serializers.ModelSerializer):
    target = CelestialTargetSerializer()

    class Meta:
        model = ExoplanetObservation
        fields = base_fields + [
            "start_observation",
            "end_observation",
        ]

    def create(self, validated_data):
        return _create_observation(validated_data, "Exoplanet", ExoplanetObservation)


class VariableObservationSerializer(serializers.ModelSerializer):
    target = CelestialTargetSerializer()

    class Meta:
        model = VariableObservation
        fields = base_fields + ["minimum_altitude"]

    def create(self, validated_data):
        return _create_observation(validated_data, "Variable", VariableObservation)


class MonitoringObservationSerializer(serializers.ModelSerializer):
    target = CelestialTargetSerializer()

    class Meta:
        model = MonitoringObservation
        fields = base_fields + [
            "frames_per_filter",
            "start_scheduling",
            "end_scheduling",
            "cadence",
        ]

    def create(self, validated_data):
        return _create_observation(validated_data, "Monitoring", MonitoringObservation)


class ExpertObservationSerializer(serializers.ModelSerializer):
    target = CelestialTargetSerializer()

    class Meta:
        model = ExpertObservation
        fields = base_fields + [
            "frames_per_filter",
            "dither_every",
            "binning",
            "subframe",
            "gain",
            "offset",
            "start_observation",
            "end_observation",
            "start_scheduling",
            "end_scheduling",
            "cadence",
            "moon_separation_angle",
            "moon_separation_width",
            "minimum_altitude",
            "priority",
        ]

    def create(self, validated_data):
        return _create_observation(validated_data, "Expert", ExpertObservation)

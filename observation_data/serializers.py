"""
Serializers for the observation_data app models.
For a usage example, see the create_observation view in the views.py file.
"""

from datetime import datetime, timezone
from decimal import Decimal

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
    validated_data["project_completion"] = 0.0
    validated_data["created_at"] = datetime.now(timezone.utc)

    if observation_type in priorities:
        validated_data["priority"] = priorities[observation_type]

    observation = model.objects.create(target=created_target, **validated_data)
    return observation


def _check_overlapping_observation(start_observation, end_observation) -> list:
    """
    Check if an observation overlaps with any existing observations.
    :param start_observation: Start time of the observation
    :param end_observation: End time of the observation
    :return: List of overlapping observations
    """
    overlapping_exoplanet = list(
        ExoplanetObservation.objects.filter(
            start_observation__lt=end_observation,
            end_observation__gt=start_observation,
        )
    )
    overlapping_expert = list(
        ExpertObservation.objects.filter(
            start_observation__lt=end_observation,
            end_observation__gt=start_observation,
        )
    )
    return overlapping_exoplanet + overlapping_expert


def _validate_time_range(start_time, end_time):
    """
    Validate that the start time is before the end time.
    :param start_time: Start time
    :param end_time: End time
    :return: None
    """
    if start_time and end_time and start_time >= end_time:
        raise serializers.ValidationError("Start time must be before end time")

    overlapping = _check_overlapping_observation(start_time, end_time)
    if len(overlapping) != 0:
        overlapping_data = ExoplanetObservationSerializer(overlapping, many=True).data
        raise serializers.ValidationError(
            {"overlapping_observations": overlapping_data}
        )


def _convert_decimal_fields(ret):
    if isinstance(ret, dict):
        return {key: _convert_decimal_fields(value) for key, value in ret.items()}
    elif isinstance(ret, list):
        return [_convert_decimal_fields(item) for item in ret]
    elif isinstance(ret, Decimal):
        return float(ret)
    return ret


# noinspection PyTypeChecker
def _to_representation(instance, additional_fields=None, exposure_fields=None):
    # Base fields that are common
    ret = {
        "name": f"{instance.observation_type}_{"".join(instance.filter_set.split(","))}_{instance.target.name}",
        "id": str(instance.user.id),
        "active": True,
        "priority": instance.priority,
        "ditherEvery": 1,
        "minimumAltitude": 35.0,
        "horizonOffset": instance.observatory.horizon_offset,
        "centerTargets": True,
        "imageGrader": {
            "minStars": instance.observatory.min_stars,
            "maxHFR": instance.observatory.max_HFR,
            "maxGuideError": instance.observatory.max_guide_error,
        },
        "targetSelectionPriority": ["COMPLETION", "ALTITUDE"],
        "targets": [],
    }

    targets = [
        {
            "name": instance.target.name,
            "RA": instance.target.ra,
            "DEC": instance.target.dec,
            "startDateTime": "",
            "endDateTime": "",
            "exposureSelectionPriority": ["N_COMPLETION", "SELECTIVITY"],
            "exposures": [],
        }
    ]

    if additional_fields and additional_fields["targets"]:
        targets[0].update(additional_fields["targets"][0])
        additional_fields.pop("targets")

    ret["targets"] = targets

    if additional_fields:
        ret.update(additional_fields)

    # Populate the exposures dynamically based on filters
    filters = [f.strip() for f in instance.filter_set.split(",")]
    for f in filters:
        exposure_data = {
            "filter": f,
            "exposureTime": instance.exposure_time,
            "gain": 100,
            "offset": 50,
            "binning": 1,
            "moonSeparationAngle": 70.0,
            "moonSeparationWidth": 7,
            "batchSize": 10,
            "requiredAmount": 100,
            "acceptedAmount": 0,
        }

        # If exposure_fields is provided, update each exposure with the additional fields
        if exposure_fields:
            exposure_data.update(exposure_fields)

        ret["targets"][0]["exposures"].append(exposure_data)

    ret = _convert_decimal_fields(ret)
    return ret


class CelestialTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CelestialTarget
        fields = "__all__"


class ObservatorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Observatory
        fields = "__all__"


class ImagingObservationSerializer(serializers.ModelSerializer):
    target = CelestialTargetSerializer()

    class Meta:
        model = ImagingObservation
        fields = base_fields + ["frames_per_filter"]

    def create(self, validated_data):
        return _create_observation(validated_data, "Imaging", ImagingObservation)

    def to_representation(self, instance):
        exposure_fields = {"subFrame": instance.frames_per_filter}
        return _to_representation(instance=instance, exposure_fields=exposure_fields)


class ExoplanetObservationSerializer(serializers.ModelSerializer):
    target = CelestialTargetSerializer()

    class Meta:
        model = ExoplanetObservation
        fields = base_fields + [
            "start_observation",
            "end_observation",
        ]

    def validate(self, attrs):
        _validate_time_range(
            attrs.get("start_observation"), attrs.get("end_observation")
        )
        return attrs

    def create(self, validated_data):
        return _create_observation(validated_data, "Exoplanet", ExoplanetObservation)

    def to_representation(self, instance):
        additional_fields = {
            "ditherEvery": 0,
            "minimumAltitude": 30.0,
            "targets": [
                {
                    "startDateTime": str(instance.start_observation.replace(tzinfo=None)).strip(),
                    "endDateTime": str(instance.end_observation.replace(tzinfo=None)).strip(),
                    "exposureSelectionPriority": ["SELECTIVITY", "COMPLETION"],
                }
            ]
        }
        exposure_fields = {
            "gain": 0,
            "subFrame": 0.25,
            "moonSeparationAngle": 40.0,
            "moonSeparationWidth": 5,
            "batchSize": 30,
            "requiredAmount": 300,
        }
        return _to_representation(
            instance=instance, additional_fields=additional_fields, exposure_fields=exposure_fields
        )


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

    def validate(self, attrs):
        _validate_time_range(
            attrs.get("start_observation"), attrs.get("end_observation")
        )
        return attrs

    def create(self, validated_data):
        return _create_observation(validated_data, "Expert", ExpertObservation)

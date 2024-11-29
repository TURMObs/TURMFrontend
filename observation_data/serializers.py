"""
Serializers for the observation_data app models.
For a usage example, see the create_observation view in the views.py file.
"""

from collections import OrderedDict
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
    Filter,
    ObservationType,
)

priorities = {
    ObservationType.IMAGING: 10,
    ObservationType.EXOPLANET: 1000000,
    ObservationType.VARIABLE: 100000,
    ObservationType.MONITORING: 1000,
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
    created_target, created = CelestialTarget.objects.get_or_create(
        name=target_data.get("name"),
        ra=target_data.get("ra"),
        dec=target_data.get("dec"),
    )

    validated_data["project_status"] = "Pending Upload"
    validated_data["project_completion"] = 0.0
    validated_data["created_at"] = datetime.now(timezone.utc)

    if observation_type in priorities:
        validated_data["priority"] = priorities[observation_type]

    filter_set = validated_data.pop("filter_set")
    observation = model.objects.create(target=created_target, **validated_data)
    observation.filter_set.set(filter_set)
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


def _convert_decimal_fields(rep):
    """
    Convert all Decimal fields to float, as Decimal is not JSON serializable.
    :param rep: Dictionary to convert
    """
    if isinstance(rep, dict):
        return {key: _convert_decimal_fields(value) for key, value in rep.items()}
    elif isinstance(rep, list):
        return [_convert_decimal_fields(item) for item in rep]
    elif isinstance(rep, Decimal):
        return float(rep)
    return rep


# noinspection PyTypeChecker
def _to_representation(instance, additional_fields=None, exposure_fields=None):
    """
    Convert an observation instance to a dictionary representation.
    :param instance: Observation instance
    :param additional_fields: Additional fields to add to the representation
    :param exposure_fields: Additional fields to add to each exposure. Do not add these to additional_fields.
    :return: Dictionary representation of the observation
    """
    rep = {
        "name": f"{instance.observation_type}_{''.join([f.filter_type for f in instance.filter_set.all()])}_{instance.target.name}",
        "id": str(instance.user.id),
        "active": True,
        "priority": instance.priority,
        "ditherEvery": 0,
        "minimumAltitude": 30.0,
        "horizonOffset": instance.observatory.horizon_offset,
        "centerTargets": True,
        "imageGrader": {
            "minStars": instance.observatory.min_stars,
            "maxHFR": instance.observatory.max_HFR,
            "maxGuideError": instance.observatory.max_guide_error,
        },
        "targetSelectionPriority": ["ALTITUDE", "COMPLETION"],
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

    if additional_fields and "targets" in additional_fields:
        targets[0].update(additional_fields["targets"][0])
        additional_fields.pop("targets")

    rep["targets"] = targets

    if additional_fields:
        rep.update(additional_fields)

    # Populate the exposures dynamically based on filters
    exposure_settings = instance.observatory.exposure_settings.filter(
        observatoryexposuresettings__observation_type=instance.observation_type,
        observatoryexposuresettings__observatory=instance.observatory,
    )

    if (
        not exposure_settings.exists()
        and instance.observation_type != ObservationType.EXPERT
    ):
        raise serializers.ValidationError(
            f"Exposure settings for observatory {instance.observatory.name} and observation type {instance.observation_type} not found"
        )

    exposure_settings = exposure_settings.first()
    exposure_order = [
        "filter",
        "exposureTime",
        "gain",
        "offset",
        "binning",
        "subFrame",
        "moonSeparationAngle",
        "moonSeparationWidth",
        "batchSize",
        "requiredAmount",
        "acceptedAmount",
    ]

    for f in instance.filter_set.all():
        exposure_data = {
            "filter": f.filter_type,
            "exposureTime": instance.exposure_time,
            "moonSeparationAngle": f.moon_separation_angle,
            "moonSeparationWidth": f.moon_separation_width,
            "batchSize": 10,
            "acceptedAmount": 0,
        }
        # If exposure_fields is provided, update each exposure with the additional fields
        if exposure_fields:
            exposure_data.update(exposure_fields)

        if exposure_settings:
            exposure_data.update(
                {
                    "gain": exposure_settings.gain,
                    "offset": exposure_settings.offset,
                    "binning": exposure_settings.binning,
                    "subFrame": exposure_settings.subFrame,
                }
            )

        ordered = OrderedDict(
            (key, exposure_data.get(key, None)) for key in exposure_order
        )
        rep["targets"][0]["exposures"].append(ordered)

    rep = _convert_decimal_fields(rep)
    return rep


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
    filter_set = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Filter.objects.all()
    )

    class Meta:
        model = ImagingObservation
        fields = base_fields + ["frames_per_filter", "required_amount"]

    def create(self, validated_data):
        return _create_observation(
            validated_data, ObservationType.IMAGING, ImagingObservation
        )

    def to_representation(self, instance):
        additional_fields = {
            "ditherEvery": 1,
        }
        exposure_fields = {
            "requiredAmount": instance.required_amount,
        }
        return _to_representation(
            instance=instance,
            exposure_fields=exposure_fields,
            additional_fields=additional_fields,
        )


class ExoplanetObservationSerializer(serializers.ModelSerializer):
    target = CelestialTargetSerializer()
    filter_set = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Filter.objects.all()
    )

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
        return _create_observation(
            validated_data, ObservationType.EXOPLANET, ExoplanetObservation
        )

    def to_representation(self, instance):
        additional_fields = {
            "targets": [
                {
                    "startDateTime": str(
                        instance.start_observation.replace(tzinfo=None)
                    ).strip(),
                    "endDateTime": str(
                        instance.end_observation.replace(tzinfo=None)
                    ).strip(),
                }
            ],
        }
        exposure_fields = {
            "requiredAmount": 1000,
        }
        return _to_representation(
            instance=instance,
            additional_fields=additional_fields,
            exposure_fields=exposure_fields,
        )


class VariableObservationSerializer(serializers.ModelSerializer):
    target = CelestialTargetSerializer()
    filter_set = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Filter.objects.all()
    )

    class Meta:
        model = VariableObservation
        fields = base_fields + ["minimum_altitude", "required_amount"]

    def create(self, validated_data):
        return _create_observation(
            validated_data, ObservationType.VARIABLE, VariableObservation
        )

    def to_representation(self, instance):
        additional_fields = {
            "minimumAltitude": instance.minimum_altitude,
        }
        exposure_fields = {
            "requiredAmount": instance.required_amount,
        }
        return _to_representation(
            instance=instance,
            additional_fields=additional_fields,
            exposure_fields=exposure_fields,
        )


class MonitoringObservationSerializer(serializers.ModelSerializer):
    target = CelestialTargetSerializer()
    filter_set = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Filter.objects.all()
    )

    class Meta:
        model = MonitoringObservation
        fields = base_fields + [
            "frames_per_filter",
            "start_scheduling",
            "end_scheduling",
            "cadence",
            "required_amount",
        ]

    def create(self, validated_data):
        return _create_observation(
            validated_data, ObservationType.MONITORING, MonitoringObservation
        )

    def to_representation(self, instance):
        exposure_fields = {
            "requiredAmount": instance.required_amount,
        }
        return _to_representation(
            instance=instance,
            exposure_fields=exposure_fields,
        )


class ExpertObservationSerializer(serializers.ModelSerializer):
    target = CelestialTargetSerializer()
    filter_set = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Filter.objects.all()
    )

    class Meta:
        model = ExpertObservation
        fields = base_fields + [
            "frames_per_filter",
            "dither_every",
            "binning",
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
            "required_amount",
        ]

    def validate(self, attrs):
        _validate_time_range(
            attrs.get("start_observation"), attrs.get("end_observation")
        )
        return attrs

    def create(self, validated_data):
        return _create_observation(
            validated_data, ObservationType.EXPERT, ExpertObservation
        )

    def to_representation(self, instance):
        additional_fields = {
            "ditherEvery": instance.dither_every,
            "minimumAltitude": instance.minimum_altitude,
            "priority": instance.priority,
            "cadence": instance.cadence,
            "targets": [
                {
                    "startDateTime": str(
                        instance.start_observation.replace(tzinfo=None)
                    ).strip(),
                    "endDateTime": str(
                        instance.end_observation.replace(tzinfo=None)
                    ).strip(),
                    "startDateTimeScheduling": str(
                        instance.start_scheduling.replace(tzinfo=None)
                    ).strip(),
                    "endDateTimeScheduling": str(
                        instance.end_scheduling.replace(tzinfo=None)
                    ).strip(),
                }
            ],
        }
        exposure_fields = {
            "subFrame": instance.frames_per_filter,
            "binning": instance.binning,
            "gain": instance.gain,
            "offset": instance.offset,
            "moonSeparationAngle": instance.moon_separation_angle,
            "moonSeparationWidth": instance.moon_separation_width,
            "requiredAmount": instance.required_amount,
        }
        return _to_representation(
            instance=instance,
            additional_fields=additional_fields,
            exposure_fields=exposure_fields,
        )


serializer_mapping = {
    ImagingObservation: ImagingObservationSerializer,
    ExoplanetObservation: ExoplanetObservationSerializer,
    VariableObservation: VariableObservationSerializer,
    MonitoringObservation: MonitoringObservationSerializer,
    ExpertObservation: ExpertObservationSerializer,
}

type_serializer_mapping = {
    ObservationType.IMAGING: ImagingObservationSerializer,
    ObservationType.EXOPLANET: ExoplanetObservationSerializer,
    ObservationType.VARIABLE: VariableObservationSerializer,
    ObservationType.MONITORING: MonitoringObservationSerializer,
    ObservationType.EXPERT: ExpertObservationSerializer,
}


def get_serializer(observation_type):
    """
    Get the serializer for a given observation type.
    :param observation_type: Type of observation
    :return: Serializer for the observation or None if not found
    """
    if observation_type in type_serializer_mapping:
        return type_serializer_mapping[observation_type]
    if observation_type in serializer_mapping:
        return serializer_mapping[observation_type]
    return None

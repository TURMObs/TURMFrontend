"""
Serializers for the observation_data app models.
For a usage example, see the create_observation view in the views.py file.
"""

from collections import OrderedDict
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .data_verification import (
    verify_field_integrity,
    validate_observation_time,
    verify_filter_selection,
    validate_schedule_time,
)
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
    ObservationStatus,
    ScheduledObservation,
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
    Create a model instance of an observation model.
    :param validated_data: Data to create the observation
    :param observation_type: Type of observation
    :param model: Model to create
    :return: Created observation

    """
    target_data = validated_data.pop("target")
    created_target = _get_or_create_celestial_target_from_data(target_data)

    # Set default values
    validated_data["project_status"] = ObservationStatus.PENDING
    validated_data["project_completion"] = 0.0
    validated_data["created_at"] = timezone.now()

    if observation_type in priorities:
        validated_data["priority"] = priorities[observation_type]

    if issubclass(model, ScheduledObservation) and "start_scheduling" in validated_data:
        validated_data["next_upload"] = validated_data["start_scheduling"]

    filter_set = validated_data.pop("filter_set")
    observation = model.objects.create(target=created_target, **validated_data)
    observation.filter_set.set(filter_set)
    return observation


def _update_observation(validated_data, existing_observation, observation_type, model):
    """
    Updates an existing observation model with new data.
    The existing observation is deleted and a new one is created with the updated data.
    Properties like created_at will be re-used from the existing observation.
    :param validated_data: Data to update the observation
    :param existing_observation: The existing observation to be updated
    :param observation_type: New observation type, possibly different from existing type
    :param model: The model class of the observation
    :return: Updated observation instance
    """
    target_data = validated_data.pop("target")
    created_target = _get_or_create_celestial_target_from_data(target_data)

    validated_data["project_status"] = ObservationStatus.PENDING
    validated_data["project_completion"] = 0.0
    validated_data["created_at"] = existing_observation.created_at

    if observation_type in priorities:
        validated_data["priority"] = existing_observation.priority

    if issubclass(model, ScheduledObservation):
        validated_data["next_upload"] = validated_data["start_scheduling"]

    filter_set = validated_data.pop("filter_set")
    observation = model.objects.create(target=created_target, **validated_data)
    observation.filter_set.set(filter_set)
    existing_observation.delete()
    return observation


def _get_or_create_celestial_target_from_data(target_data):
    catalog_id = target_data.get("catalog_id")
    if not catalog_id:
        target_data["catalog_id"] = ""

    created_target, created = CelestialTarget.objects.get_or_create(
        name=target_data.get("name"),
        catalog_id=target_data.get("catalog_id"),
        ra=target_data.get("ra"),
        dec=target_data.get("dec"),
    )
    return created_target


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
        "id": str(instance.user.username),
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
        if exposure_settings:
            exposure_data.update(
                {
                    "gain": exposure_settings.gain,
                    "offset": exposure_settings.offset,
                    "binning": exposure_settings.binning,
                    "subFrame": exposure_settings.subframe,
                }
            )

        if exposure_fields:
            exposure_data.update(exposure_fields)

        ordered = OrderedDict(
            (key, exposure_data.get(key, None)) for key in exposure_order
        )
        rep["targets"][0]["exposures"].append(ordered)

    rep = _convert_decimal_fields(rep)
    return rep


def _validate_fields(
        attrs, validate_times=False, validate_scheduling=False, exclude_observation_ids=None, return_errors=False
):
    if exclude_observation_ids is None:
        exclude_observation_ids = []
    errors = {}
    observation_type = attrs.get("observation_type")
    for name, value in attrs.items():
        error = verify_field_integrity(name, value, observation_type)
        if error:
            errors = {**errors, **error}

    if "filter_set" in attrs:
        observatory = attrs.get("observatory")
        filters = attrs.get("filter_set")
        filter_errors = verify_filter_selection(filters, observatory)
        if filter_errors:
            errors = {**errors, **filter_errors}

    if validate_times:
        time_errors = validate_observation_time(
            attrs.get("start_observation"),
            attrs.get("end_observation"),
            attrs.get("observatory"),
            exclude_observation_ids,
        )
        if time_errors:
            errors = {**errors, **time_errors}

    if validate_scheduling:
        if not attrs.get("start_scheduling") or not attrs.get("end_scheduling") and not observation_type == ObservationType.EXPERT:
            errors["scheduling"] = "Both scheduling times are required."
        if attrs.get("start_scheduling") and attrs.get("end_scheduling"):
            time_errors = validate_schedule_time(
                attrs.get("start_scheduling"),
                attrs.get("end_scheduling"),
            )
            if time_errors:
                errors = {**errors, **time_errors}

    if return_errors:
        return errors

    if errors:
        raise serializers.ValidationError(errors)


class CelestialTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CelestialTarget
        fields = "__all__"

    def validate(self, attrs):
        _validate_fields(attrs)
        return attrs


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
        fields = base_fields + ["frames_per_filter"]

    def validate(self, attrs):
        _validate_fields(attrs)
        return attrs

    def create(self, validated_data):
        return _create_observation(
            validated_data, ObservationType.IMAGING, ImagingObservation
        )

    def update(self, instance, validated_data):
        return _update_observation(
            validated_data, instance, ObservationType.IMAGING, ImagingObservation
        )

    def to_representation(self, instance):
        additional_fields = {
            "ditherEvery": 1,
        }
        exposure_fields = {
            "requiredAmount": instance.frames_per_filter,
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
        _validate_fields(
            attrs,
            exclude_observation_ids=[self.instance.id] if self.instance else [],
            validate_times=True,
        )
        return attrs

    def create(self, validated_data):
        return _create_observation(
            validated_data, ObservationType.EXOPLANET, ExoplanetObservation
        )

    def update(self, instance, validated_data):
        return _update_observation(
            validated_data, instance, ObservationType.EXOPLANET, ExoplanetObservation
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
        fields = base_fields + ["minimum_altitude", "frames_per_filter"]

    def validate(self, attrs):
        _validate_fields(attrs)
        return attrs

    def create(self, validated_data):
        return _create_observation(
            validated_data, ObservationType.VARIABLE, VariableObservation
        )

    def update(self, instance, validated_data):
        return _update_observation(
            validated_data, instance, ObservationType.VARIABLE, VariableObservation
        )

    def to_representation(self, instance):
        additional_fields = {
            "minimumAltitude": instance.minimum_altitude,
        }
        exposure_fields = {
            "requiredAmount": instance.frames_per_filter,
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
        ]

    def validate(self, attrs):
        _validate_fields(attrs=attrs, validate_scheduling=True,
                         exclude_observation_ids=[self.instance.id] if self.instance else [])
        return attrs

    def create(self, validated_data):
        return _create_observation(
            validated_data, ObservationType.MONITORING, MonitoringObservation
        )

    def update(self, instance, validated_data):
        return _update_observation(
            validated_data, instance, ObservationType.MONITORING, MonitoringObservation
        )

    def to_representation(self, instance):
        exposure_fields = {
            "requiredAmount": instance.frames_per_filter,
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
            "subframe",
            "gain",
            "offset",
            "start_observation",
            "end_observation",
            "start_observation_time",
            "end_observation_time",
            "start_scheduling",
            "end_scheduling",
            "cadence",
            "moon_separation_angle",
            "moon_separation_width",
            "minimum_altitude",
            "priority",
        ]

    def validate(self, attrs):
        exclude_ids = [self.instance.id] if self.instance else []
        errors = _validate_fields(
            attrs,
            exclude_observation_ids=exclude_ids,
            return_errors=True
        )
        start_observation = attrs.get("start_observation")
        end_observation = attrs.get("end_observation")
        start_observation_time = attrs.get("start_observation_time")
        end_observation_time = attrs.get("end_observation_time")
        start_scheduling = attrs.get("start_scheduling")
        end_scheduling = attrs.get("end_scheduling")
        if start_scheduling or end_scheduling:
            # Scheduled observations with times instead of dates
            if not (start_scheduling and end_scheduling):
                print(start_scheduling, end_scheduling)
                errors["scheduling"] = "Both scheduling times are required."
            if start_observation or end_observation:
                errors["observation_dates"] = "Observation dates not allowed for scheduled observations."
            if (start_observation_time or end_observation_time) and not (start_observation_time and end_observation_time):
                errors["observation_time"] = "Both observation times are required."
            if start_observation_time and end_observation_time:
                time_errors = validate_observation_time(
                    start_observation_time,
                    end_observation_time,
                    attrs.get("observatory"),
                    exclude_ids,
                )
                if time_errors:
                    errors = {**errors, **time_errors}

            schedule_errors = validate_schedule_time(
                start_scheduling,
                end_scheduling,
            )
            if schedule_errors:
                errors = {**errors, **schedule_errors}

        else:
            # Unscheduled observations with possible observation date
            if (start_observation or end_observation) and not (start_observation and end_observation):
                errors["observation_dates"] = "Both observation dates are required."
            if start_observation_time or end_observation_time:
                errors["observation_time"] = "Observation times not allowed for unscheduled observations."
            if start_observation and end_observation:
                time_errors = validate_observation_time(
                    start_observation,
                    end_observation,
                    attrs.get("observatory"),
                    exclude_ids,
                )
                if time_errors:
                    errors = {**errors, **time_errors}

        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        return _create_observation(
            validated_data, ObservationType.EXPERT, ExpertObservation
        )

    def update(self, instance, validated_data):
        return _update_observation(
            validated_data, instance, ObservationType.EXPERT, ExpertObservation
        )

    def to_representation(self, instance):
        additional_fields = {
            "ditherEvery": instance.dither_every,
            "minimumAltitude": instance.minimum_altitude,
            "priority": instance.priority,
            "cadence": instance.cadence,
        }

        if instance.start_scheduling and instance.end_scheduling:
            additional_fields["targets"] = [{
                "startDateTime": str(
                    instance.start_scheduling.replace(tzinfo=None)
                ).strip(),
                "endDateTime": str(
                    instance.end_scheduling.replace(tzinfo=None)
                ).strip()
            }]

        exposure_fields = {
            "subFrame": instance.subframe,
            "binning": instance.binning,
            "gain": instance.gain,
            "offset": instance.offset,
            "moonSeparationAngle": instance.moon_separation_angle,
            "moonSeparationWidth": instance.moon_separation_width,
            "requiredAmount": instance.frames_per_filter,
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
    try:
        if observation_type in type_serializer_mapping:
            return type_serializer_mapping[observation_type]
        if observation_type in serializer_mapping:
            return serializer_mapping[observation_type]
        return None
    except TypeError:
        return None

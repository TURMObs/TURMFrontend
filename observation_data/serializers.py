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


class CelestialTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CelestialTarget
        fields = ["catalog_id", "name", "ra", "dec"]

    def validate(self, data):
        return data

def create_observation(data, target_data, observation_type, model):
    created_target, _ = CelestialTarget.objects.get_or_create(
        catalog_id=target_data["catalog_id"],
        defaults={
            "name": target_data["name"],
            "ra": target_data["ra"],
            "dec": target_data["dec"],
        },
    )

    data["project_status"] = "Pending Upload"
    if observation_type in priorities:
        data["priority"] = priorities[observation_type]

    observation = model.objects.create(target=created_target, **data)
    return observation


class ObservatorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Observatory
        fields = [
            "name",
            "horizonOffset",
            "min_stars",
            "max_HFR",
            "max_guide_error",
            "filter_set",
        ]



class ImagingObservationSerializer(serializers.ModelSerializer):
    target = CelestialTargetSerializer()
    frames_per_filter = serializers.IntegerField()

    class Meta:
        model = ImagingObservation
        fields = base_fields + ["frames_per_filter"]

    def resolve_target(self, data):
        target_data = data.pop("target")
        created_target, _ = CelestialTarget.objects.get_or_create(
            catalog_id=target_data["catalog_id"],
            defaults={
                "name": target_data["name"],
                "ra": target_data["ra"],
                "dec": target_data["dec"],
            },
        )
        target_serializer = CelestialTargetSerializer(created_target)
        print("created_target: ", target_serializer.data)
        data["target"] = target_serializer.data
        return data


    def create(self, validated_data):
        target_data = validated_data.pop("target")
        created_target, _ = CelestialTarget.objects.get_or_create(
            catalog_id=target_data["catalog_id"],
            defaults={
                "name": target_data["name"],
                "ra": target_data["ra"],
                "dec": target_data["dec"],
            },
        )

        validated_data["project_status"] = "Pending Upload"
        validated_data["priority"] = priorities["Imaging"]

        observation = ImagingObservation.objects.create(target=created_target, **validated_data)
        return observation



class ExoplanetObservationSerializer(serializers.ModelSerializer):
    target = CelestialTargetSerializer()
    start_observation = serializers.DateTimeField()
    end_observation = serializers.DateTimeField()

    class Meta:
        model = ExoplanetObservation
        fields = base_fields + [
            "start_observation",
            "end_observation",
        ]

    def create(self, validated_data):
        return create_observation(validated_data, "Exoplanet", ExoplanetObservation)


class VariableObservationSerializer(serializers.ModelSerializer):
    target = CelestialTargetSerializer()
    minimum_altitude = serializers.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        model = VariableObservation
        fields = base_fields + ["minimum_altitude"]

    def create(self, validated_data):
        return create_observation(validated_data, "Variable", VariableObservation)


class MonitoringObservationSerializer(serializers.ModelSerializer):
    target = CelestialTargetSerializer()
    frames_per_filter = serializers.IntegerField()
    start_scheduling = serializers.DateTimeField()
    end_scheduling = serializers.DateTimeField()
    cadence = serializers.DurationField()

    class Meta:
        model = MonitoringObservation
        fields = base_fields + [
            "frames_per_filter",
            "start_scheduling",
            "end_scheduling",
            "cadence",
        ]

    def create(self, validated_data):
        return create_observation(validated_data, "Monitoring", MonitoringObservation)


class ExpertObservationSerializer(serializers.ModelSerializer):
    target = CelestialTargetSerializer()
    frames_per_filter = serializers.IntegerField()
    dither_every = serializers.DecimalField(max_digits=5, decimal_places=2)
    binning = serializers.CharField(max_length=50)
    subframe = serializers.CharField(max_length=50)
    gain = serializers.IntegerField()
    offset = serializers.IntegerField()
    start_observation = serializers.DateTimeField()
    end_observation = serializers.DateTimeField()
    start_scheduling = serializers.DateTimeField()
    end_scheduling = serializers.DateTimeField()
    cadence = serializers.DurationField()
    moon_separation_angle = serializers.DecimalField(max_digits=5, decimal_places=2)
    moon_separation_width = serializers.IntegerField()
    minimum_altitude = serializers.DecimalField(max_digits=5, decimal_places=2)

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
        ]

    def create(self, validated_data):
        return create_observation(validated_data, "Expert", ExpertObservation)

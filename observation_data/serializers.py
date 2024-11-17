from rest_framework import serializers
from .models import ExoplanetObservation, CelestialTarget


class CelestialTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CelestialTarget
        fields = ["name", "coordinates"]


class ExoplanetObservationSerializer(serializers.ModelSerializer):
    target = CelestialTargetSerializer()

    class Meta:
        model = ExoplanetObservation
        fields = ["observatory", "target", "filter_set"]

    def create(self, validated_data):
        target_data = validated_data.pop("target")
        target_name = target_data.get("name")
        target, created = CelestialTarget.objects.get_or_create(
            name=target_name, defaults={"coordinates": target_data.get("coordinates")}
        )
        observation = ExoplanetObservation.objects.create(
            target=target, **validated_data
        )
        return observation

    def validate(self, data):
        return data

import re

from rest_framework import serializers

from observation_data.models import ExoplanetObservation, ExpertObservation


def _assert_number_in_range(name, value, min_value, max_value):
    """
    Assert that a number is within a specified range.
    :param name: Name of the attribute
    :param value: Number to check
    :param min_value: Inclusive minimum value
    :param max_value: Inclusive maximum value
    :return: None
    :raises: serializers.ValidationError if the value is not in the specified range
    """
    if value < min_value or value > max_value:
        raise serializers.ValidationError(
            {name: f"Must be between {min_value} and {max_value}"}
        )


def _assert_matches_regex(name, value, regex):
    """
    Assert that a string matches a specified regex pattern.
    :param name: Name of the attribute
    :param value: String to check
    :param regex: Regex pattern to match
    :return: None
    :raises: serializers.ValidationError if the string does not match the pattern
    """

    if not re.fullmatch(regex, value):
        raise serializers.ValidationError({name: "Invalid format"})


def verify_data_integrity(name, value):
    """
    Verify data integrity.
    :param name: Name of the attribute
    :param value: Value of the attribute
    :return: None
    :raises: serializers.ValidationError if the value is invalid
    """
    if isinstance(value, dict) or isinstance(value, list):
        return

    if name == "frames_per_filter":
        _assert_number_in_range(name, value, 1, 10000)
    elif name == "required_amount":
        _assert_number_in_range(name, value, 1, 100000)
    elif name == "ra":
        _assert_matches_regex(name, value, r"\d{2} \d{2} \d{2}(?:\.\d{1,7})?")
    elif name == "dec":
        _assert_matches_regex(name, value, r"[+-]?\d{2} \d{2} \d{2}(?:\.\d{1,5})?")
    elif name == "exposure_time":
        _assert_number_in_range(name, value, 0.1, 3600)
    elif name == "name":
        if not isinstance(value, str):
            raise serializers.ValidationError({"Must be a string"})
    elif name == "catalog_id":
        if not isinstance(value, str):
            raise serializers.ValidationError({"Must be a string"})


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


def validate_time_range(start_time, end_time):
    """
    Validate that the start time is before the end time.
    :param start_time: Start time
    :param end_time: End time
    :return: None
    """
    from observation_data.serializers import ExoplanetObservationSerializer

    if start_time and end_time and start_time >= end_time:
        raise serializers.ValidationError("Start time must be before end time")

    overlapping = _check_overlapping_observation(start_time, end_time)
    if len(overlapping) != 0:
        overlapping_data = ExoplanetObservationSerializer(overlapping, many=True).data
        raise serializers.ValidationError(
            {"overlapping_observations": overlapping_data}
        )

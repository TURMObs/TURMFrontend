import decimal
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
    :return: Error if the value is not within the specified range
    """
    if not isinstance(value, (int, float, decimal.Decimal)):
        return {name: "Must be a number."}
    if value < min_value or value > max_value:
        return {name: f"Must be between {min_value} and {max_value}."}


def _assert_matches_regex(name, value, regex):
    """
    Assert that a string matches a specified regex pattern.
    :param name: Name of the attribute
    :param value: String to check
    :param regex: Regex pattern to match
    :return: Error if the value does not match the regex pattern
    """

    if not re.fullmatch(regex, value):
        return {name: "Invalid format."}


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


def verify_field_integrity(name, value):
    """
    Verify data integrity.
    :param name: Name of the attribute
    :param value: Value of the attribute
    :return: Error if the value is invalid or None if the value is valid
    """
    if isinstance(value, dict) or isinstance(value, list):
        return

    match name:
        case "frames_per_filter":
            return _assert_number_in_range(name, value, 1, 10000)
        case "required_amount":
            return _assert_number_in_range(name, value, 1, 100000)
        case "ra":
            return _assert_matches_regex(
                name, value, r"\d{2} \d{2} \d{2}(?:\.\d{1,7})?"
            )
        case "dec":
            return _assert_matches_regex(
                name, value, r"[+-]?\d{2} \d{2} \d{2}(?:\.\d{1,5})?"
            )
        case "exposure_time":
            return _assert_number_in_range(name, value, 0.1, 3600)
        case "dither_every":
            return _assert_number_in_range(name, value, 0.0, 10.0)
        case "binning":
            return _assert_number_in_range(name, value, 0, 10)
        case "gain":
            return _assert_number_in_range(name, value, 0, 10000)
        case "offset":
            return _assert_number_in_range(name, value, 0, 10000)
        case "cadence":
            return _assert_number_in_range(name, value, 1, 1000)
        case "moon_separation_angle":
            return _assert_number_in_range(name, value, 0.0, 180.0)
        case "moon_separation_width":
            return _assert_number_in_range(name, value, 0, 100)
        case "minimum_altitude":
            return _assert_number_in_range(name, value, 0.0, 90.0)
        case "priority":
            return _assert_number_in_range(name, value, 1, 10000000)
        case "name":
            if not isinstance(value, str):
                return {"Must be a string."}
        case "catalog_id":
            if not isinstance(value, str):
                return {"Must be a string."}
        case (
            "observatory"
            | "user"
            | "start_observation"
            | "end_observation"
            | "start_scheduling"
            | "end_scheduling"
            | "observation_type"
        ):
            return None
        case _:
            return {name: "Unknown field."}


def verify_filter_selection(filters, observatory):
    """
    Validate that the selected filters are valid and available at the observatory.
    :param filters: List of filters
    :param observatory: Observatory
    :return: List of errors if the filters are invalid or None
    """
    available = observatory.filter_set.all()
    errors = {}
    for f in filters:
        if f in available:
            continue
        errors.setdefault("filter_set", []).append(
            f"Filter {f.filter_type} is not available at observatory {observatory.name}."
        )

    return errors


def validate_time_range(start_time, end_time):
    """
    Validate that the start time is before the end time and that the observation does not overlap with existing observations.
    :param start_time: Start time
    :param end_time: End time
    :return: None
    """
    from observation_data.serializers import ExoplanetObservationSerializer

    if start_time and end_time and start_time >= end_time:
        raise serializers.ValidationError("Start time must be before end time.")

    overlapping = _check_overlapping_observation(start_time, end_time)
    if len(overlapping) != 0:
        # note: this is a compromise, as ExoplanetObservation and ExpertObservation have different serializers but ExoplanetObservationSerializer works for both (but looses some data)
        overlapping_data = ExoplanetObservationSerializer(overlapping, many=True).data
        raise serializers.ValidationError(
            {"overlapping_observations": overlapping_data}
        )

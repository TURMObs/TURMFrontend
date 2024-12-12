import decimal
import logging
import re

from rest_framework import serializers

from observation_data.models import (
    ExoplanetObservation,
    ExpertObservation,
    ObservationType,
)

logger = logging.getLogger(__name__)


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


def _assert_in_choices(name, value, choices):
    """
    Assert that a value is within a specified list of choices.
    :param name: Name of the attribute
    :param value: Value to check
    :param choices: List of valid choices
    :return: Error if the value is not within the specified list of choices
    """
    if value not in choices:
        return {name: f"Must be one of {choices}."}


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


def _check_overlapping_observation(
    start_observation, end_observation, observatory
) -> list:
    """
    Check if an observation overlaps with any existing observations.
    :param start_observation: Start time of the observation
    :param end_observation: End time of the observation
    :param observatory: Observatory name
    :return: List of overlapping observations
    """
    overlapping_exoplanet = list(
        ExoplanetObservation.objects.filter(
            observatory=observatory,
            start_observation__lt=end_observation,
            end_observation__gt=start_observation,
        )
    )
    overlapping_expert = list(
        ExpertObservation.objects.filter(
            observatory=observatory,
            start_observation__lt=end_observation,
            end_observation__gt=start_observation,
        )
    )
    return overlapping_exoplanet + overlapping_expert


def verify_field_integrity(name, value, observation_type):
    """
    Verify data integrity.
    :param name: Name of the attribute
    :param value: Value of the attribute
    :param observation_type: Type of observation
    :return: Error if the value is invalid or None if the value is valid
    """
    if isinstance(value, dict) or isinstance(value, list):
        return

    match name:
        case "frames_per_filter":
            return _assert_number_in_range(name, value, 1, 1000)
        case "required_amount":
            return _assert_number_in_range(name, value, 1, 1000)
        case "ra":
            return _assert_matches_regex(
                name, value, r"\d{2} \d{2} \d{2}(?:\.\d{1,7})?"
            )
        case "dec":
            return _assert_matches_regex(
                name, value, r"[+-]?\d{2} \d{2} \d{2}(?:\.\d{1,5})?"
            )
        case "exposure_time":
            if observation_type == ObservationType.EXPERT:
                return _assert_number_in_range(name, value, 1, 1800)
            else:
                return _assert_in_choices(name, value, [30, 60, 120, 300])
        case "dither_every":
            return _assert_number_in_range(name, value, 0, 100)
        case "binning":
            return _assert_in_choices(name, value, [1, 2, 3])
        case "gain":
            return _assert_number_in_range(name, value, 0, 5000)
        case "offset":
            return _assert_number_in_range(name, value, 0, 1000)
        case "cadence":
            return _assert_number_in_range(name, value, 0, 14)
        case "moon_separation_angle":
            return _assert_number_in_range(name, value, 0.0, 180.0)
        case "moon_separation_width":
            return _assert_number_in_range(name, value, 0, 14)
        case "minimum_altitude":
            return _assert_number_in_range(name, value, 0.0, 60.0)
        case "priority":
            return _assert_number_in_range(name, value, 1, 10_000_000)
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


def validate_time_range(start_time, end_time, observatory):
    """
    Validate that the start time is before the end time and that the observation does not overlap with existing observations for the selected Observatory.
    :param start_time: Start time
    :param end_time: End time
    :param observatory: Observatory name
    :return: None
    """
    from observation_data.serializers import ExoplanetObservationSerializer

    if start_time and end_time and start_time >= end_time:
        raise serializers.ValidationError("Start time must be before end time.")

    overlapping = _check_overlapping_observation(start_time, end_time, observatory)
    if len(overlapping) != 0:
        # note: this is a compromise, as ExoplanetObservation and ExpertObservation have different serializers but ExoplanetObservationSerializer works for both (but looses some data)
        overlapping_data = ExoplanetObservationSerializer(overlapping, many=True).data
        raise serializers.ValidationError(
            {"overlapping_observations": overlapping_data}
        )

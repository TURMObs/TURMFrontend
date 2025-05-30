import decimal
import logging
import re
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.utils import timezone

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


def _check_for_overlap(
    start_observation: datetime,
    end_observation: datetime,
    observatory,
    exclude_observation_ids,
) -> list:
    """
    Check if an observation overlaps with any existing observations.
    :param start_observation: Start datetime of the observation
    :param end_observation: End datetime of the observation
    :param observatory: Observatory name
    :param exclude_observation_ids: List of observations to exclude from the check
    :return: List of overlapping observation times
    """
    overlapping_exoplanet = list(
        ExoplanetObservation.objects.filter(
            observatory=observatory,
            start_observation__lt=end_observation,
            end_observation__gt=start_observation,
        ).exclude(id__in=exclude_observation_ids)
    )
    overlapping_expert = list(
        ExpertObservation.objects.filter(
            observatory=observatory,
            start_observation__lt=end_observation,
            end_observation__gt=start_observation,
        ).exclude(id__in=exclude_observation_ids)
    )
    overlapping_times = []
    for overlapping in overlapping_exoplanet + overlapping_expert:
        overlapping_times.append(
            {
                "start_observation": overlapping.start_observation,
                "end_observation": overlapping.end_observation,
            }
        )
    return overlapping_times


def _check_overlapping_observation(
    start_observation,
    end_observation,
    observatory,
    exclude_observation_ids,
    start_scheduling=None,
    end_scheduling=None,
    date_included=True,
) -> list:
    """
    Check if an observation overlaps with any existing observations.
    :param start_observation: Start (date-)time of the observation
    :param end_observation: End (date-)time of the observation
    :param observatory: Observatory name
    :param exclude_observation_ids: List of observations to exclude from the check
    :param start_scheduling: Start scheduling. Used for checking overlapping observations for timed observations
    :param end_scheduling: End scheduling. Used for checking overlapping observations for timed observations
    :param date_included: Boolean indicating if the date is included in the time. If start_scheduling and end_scheduling are provided, date_included has to be False
    :return: List of overlapping observation times
    """
    if (start_scheduling or end_scheduling) and date_included:
        logger.warning(
            "Date verification failed: Date_included has to be False if start_scheduling and end_scheduling are provided."
        )
        return []

    if date_included:
        return _check_for_overlap(
            start_observation, end_observation, observatory, exclude_observation_ids
        )

    overlapping = []
    for day in range((end_scheduling - start_scheduling).days + 1):
        current_date = start_scheduling + timedelta(days=day)
        start = timezone.make_aware(
            datetime.combine(current_date, start_observation), dt_timezone.utc
        )
        end = timezone.make_aware(
            datetime.combine(current_date, end_observation), dt_timezone.utc
        )
        if end_scheduling < start_scheduling:
            end += timedelta(days=1)
        overlapping += _check_for_overlap(
            start, end, observatory, exclude_observation_ids
        )

    return overlapping


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
        case "subframe":
            return _assert_number_in_range(name, value, 0.0, 1.0)
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
        case "batch_size":
            return _assert_number_in_range(name, value, 1, 100000)
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
            | "start_observation_time"
            | "end_observation_time"
        ):
            return None
        case _:
            return {name: "Data verification encountered unknown field."}


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


def validate_observation_time(
    start_time,
    end_time,
    observatory,
    exclude_observation_ids,
    date_included=True,
    start_scheduling=None,
    end_scheduling=None,
):
    """
    Validate that the start time is before the end time and that the observation does not overlap with existing observations for the selected Observatory.
    Also checks that the start time is in the future.
    :param start_time: Start (date-)time
    :param end_time: End (date-)time
    :param observatory: Observatory name
    :param exclude_observation_ids: List of observations to exclude from the check
    :param date_included: Boolean indicating if the date is included in the time
    :param start_scheduling: Start scheduling. Used for checking overlapping observations for timed observations
    :param end_scheduling: End scheduling. Used for checking overlapping observations for timed observations
    :return: Error if the time range is invalid or None if the time range is valid
    """

    errors = {}

    overlapping = _check_overlapping_observation(
        start_time,
        end_time,
        observatory,
        exclude_observation_ids,
        start_scheduling,
        end_scheduling,
        date_included,
    )
    if len(overlapping) != 0:
        errors = {**errors, "overlapping_observations": overlapping}

    if not date_included:
        return errors

    if start_time >= end_time:
        errors = {**errors, "time_range": "Start time must be before end time."}

    if start_time < timezone.now():
        errors = {**errors, "start_time": "Start time must be in the future."}

    if start_time.year >= timezone.now().year + 10:
        errors = {
            **errors,
            "year_range": "Start time must be within the next 10 years.",
        }

    return errors


def validate_schedule_time(start_scheduling, end_scheduling):
    """
    Validate that the start time is before the end time. Also checks that the start time is in the future.
    :param start_scheduling: Start date
    :param end_scheduling: End date
    :return: Error if the time range is invalid or None if the time range is valid
    """
    errors = {}
    if start_scheduling > end_scheduling:
        errors = {
            **errors,
            "scheduling_range": "Start scheduling must be before end scheduling.",
        }
    if start_scheduling < timezone.now().date():
        errors = {
            **errors,
            "start_scheduling": "Start scheduling must be in the future.",
        }

    return errors

import logging
from enum import Enum

from django import forms
from django.db import ProgrammingError

from observation_request.TURMField import (
    TURMGridField,
    TURMField,
    TURMRadioInput,
    TURMSelectField,
    TURMDateDuration,
    TURMDateTimeDuration,
)
from observation_request.TURMInput import TURMCharInput, TURMButtonInput
from .models import (
    CelestialTarget,
    ExpertObservation,
    ObservationType,
    Observatory,
    AbstractObservation,
    ExposureSettings,
)

logger = logging.getLogger(__name__)


class Dependency(Enum):
    observation_type = "observation_type_dependent"
    observatory = "observatory_dependent"
    scheduling = "scheduling_dependent"


class CelestialTargetForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(CelestialTargetForm, self).__init__(*args, **kwargs)
        self.label_suffix = ""

    name = TURMField.init_from_model(CelestialTarget._meta.get_field("name")).add_attrs(
        {"placeholder": "OrionNebula"}
    )
    target_widgets = [
        (TURMCharInput("catalog_id", "M42"), "Catalog ID"),
        (TURMButtonInput("Fetch SIMBAD coordinates", "fetch_coordinates()"), ""),
    ]
    catalog_id = TURMGridField(target_widgets, (2, 1))
    ra = TURMField.init_from_model(
        CelestialTarget._meta.get_field("ra"), label_name="RA"
    ).add_attrs({"placeholder": "hh mm ss"})
    dec = TURMField.init_from_model(
        CelestialTarget._meta.get_field("dec"), label_name="DEC"
    ).add_attrs({"placeholder": "dd mm ss"})


class TURMProjectForm(forms.Form):
    """
    Form for selecting the Project data
    rn the Observatory
    """

    def __init__(self, *args, **kwargs):
        super(TURMProjectForm, self).__init__(*args, **kwargs)
        self.label_suffix = ""

    try:
        observatory = TURMField.init_from_model(
            model_field=AbstractObservation._meta.get_field("observatory"),
            label_name="",
        ).add_on_click(
            lambda o_type: f"disable_inputs('{Dependency.observatory.value}','{o_type}')"
        )
    except ProgrammingError as error:
        error_message = str(error).split("\n")[0]
        logger.warning(f"DB seems to be badly configured. \n{error_message}")


def filter_set_dependency_generator(filter):
    dependency = {Dependency.observatory.value: []}
    for observatory in Observatory.objects.filter(
        filter_set__filter_type__icontains=filter
    ).iterator():
        dependency[Dependency.observatory.value].append(str(observatory))
    return dependency


class ExposureSettingsForm(forms.Form):
    """
    Form for selecting the Exposure settings
    """

    def __init__(self, *args, **kwargs):
        super(ExposureSettingsForm, self).__init__(*args, **kwargs)
        self.label_suffix = ""

    try:
        observation_type = TURMSelectField(
            "observation_type",
            [(o_type[1], o_type[0]) for o_type in ObservationType.choices],
            label_name="Observation Type",
        ).add_on_click(
            lambda o_type: f"hide_inputs('{Dependency.observation_type.value}','{o_type}')"
        )
        # combined
        filter_set = (
            TURMField.init_from_model(
                ExpertObservation._meta.get_field("filter_set")
            ).add_dependency_generator(filter_set_dependency_generator)
        ).add_tooltip("This filter is not supported by the selected observatory")

        #
        exposure_time = TURMField(
            TURMRadioInput(
                name="exposure_time",
                choices=[
                    ("30s", "30"),
                    ("60s", "60"),
                    ("120s", "120"),
                    ("300s", "300"),
                ],
            ),
            label_name="Exposure Time",
        ).add_dependencies(
            {
                Dependency.observation_type.value: [
                    ObservationType.IMAGING,
                    ObservationType.EXOPLANET,
                    ObservationType.VARIABLE,
                    ObservationType.MONITORING,
                ]
            }
        )
        exposure_time_expert = (
            TURMField.init_from_model(
                AbstractObservation._meta.get_field("exposure_time"),
                label_name="Exposure Time",
            )
            .add_dependencies(
                {Dependency.observation_type.value: [ObservationType.EXPERT]}
            )
            .add_attrs({"placeholder": "default value"})
        )
        exposure_time_expert.required = False

        # exposure
        exposure_settings = [
            (
                TURMField.model_field_to_input(
                    ExpertObservation._meta.get_field("frames_per_filter")
                ).add_attrs({"placeholder": "default value"}),
                "Frames per Filter",
            ),
            (
                TURMField.model_field_to_input(
                    ExpertObservation._meta.get_field("dither_every")
                ).add_attrs({"placeholder": "default value"}),
                "Dither Every",
            ),
            (
                TURMField.model_field_to_input(
                    ExposureSettings._meta.get_field("binning")
                ).add_attrs({"placeholder": "default value"}),
                "Binning",
            ),
            (
                TURMField.model_field_to_input(
                    ExposureSettings._meta.get_field("subframe")
                ).add_attrs({"placeholder": "default value"}),
                "Sub Frame",
            ),
            (
                TURMField.model_field_to_input(
                    ExposureSettings._meta.get_field("gain")
                ).add_attrs({"placeholder": "default value"}),
                "Gain",
            ),
            (
                TURMField.model_field_to_input(
                    ExposureSettings._meta.get_field("offset")
                ).add_attrs({"placeholder": "default value"}),
                "Offset",
            ),
        ]

        exposure = TURMGridField(exposure_settings, (2, 3)).add_dependencies(
            {Dependency.observation_type.value: [ObservationType.EXPERT]}
        )
        exposure.required = False
        # imaging
        frames_per_filter = TURMField.init_from_model(
            ExpertObservation._meta.get_field("frames_per_filter"),
            label_name="Frames per Filter",
        ).add_dependencies(
            {
                Dependency.observation_type.value: [
                    ObservationType.IMAGING,
                    ObservationType.VARIABLE,
                    ObservationType.MONITORING,
                ]
            }
        )

        # exoplanet
        start_end_observation = TURMDateTimeDuration(
            (
                ExpertObservation._meta.get_field("start_observation"),
                "Start Observation",
            ),
            (ExpertObservation._meta.get_field("end_observation"), "End Observation"),
        ).add_dependencies(
            {
                Dependency.observation_type.value: [
                    ObservationType.EXOPLANET,
                    # ObservationType.EXPERT,
                ]
            }
        )
        # variable
        minimum_altitude = TURMField.init_from_model(
            ExpertObservation._meta.get_field("minimum_altitude")
        ).add_dependencies(
            {
                Dependency.observation_type.value: [
                    ObservationType.VARIABLE,
                    # ObservationType.EXPERT,
                ]
            }
        )

        # monitoring
        scheduling = TURMDateDuration(
            (ExpertObservation._meta.get_field("start_scheduling"), "Start Scheduling"),
            (ExpertObservation._meta.get_field("end_scheduling"), "End Scheduling"),
        ).add_dependencies(
            {
                Dependency.observation_type.value: [
                    ObservationType.MONITORING,
                ]
            }
        )

        cadence = TURMField.init_from_model(
            ExpertObservation._meta.get_field("cadence")
        ).add_dependencies(
            {
                Dependency.observation_type.value: [
                    ObservationType.MONITORING,
                ]
            }
        )

        # expert
        class SchedulingType(Enum):
            NO_CONSTRAINT = "No Constraint"
            SCHEDULE = "Scheduling"
            SCHEDULE_TIME = "Timed Scheduling"
            TIMED = "Timed"

        schedule_type = (
            TURMSelectField(
                "schedule_type",
                [
                    (s_val.value, s_key)
                    for s_key, s_val in SchedulingType._member_map_.items()
                ],
                label_name="Time Constrains",
            )
            .add_on_click(
                lambda s_type: f"hide_inputs('{Dependency.scheduling.value}','{s_type}')"
            )
            .add_dependencies(
                {Dependency.observation_type.value: [ObservationType.EXPERT]}
            )
        )

        exp_schedule = TURMDateDuration(
            (ExpertObservation._meta.get_field("start_scheduling"), "Start Scheduling"),
            (ExpertObservation._meta.get_field("end_scheduling"), "End Scheduling"),
        ).add_dependencies(
            {
                Dependency.observation_type.value: [
                    ObservationType.EXPERT,
                ],
                Dependency.scheduling.value: [
                    SchedulingType.SCHEDULE.name,
                    SchedulingType.SCHEDULE_TIME.name,
                ],
            }
        )

        exp_schedule_time = TURMDateDuration(
            (ExpertObservation._meta.get_field("start_observation_time"), "Start Time"),
            (ExpertObservation._meta.get_field("end_observation_time"), "End Time"),
        ).add_dependencies(
            {
                Dependency.observation_type.value: [
                    ObservationType.EXPERT,
                ],
                Dependency.scheduling.value: [SchedulingType.SCHEDULE_TIME.name],
            }
        )

        exp_cadence = (
            TURMField.init_from_model(ExpertObservation._meta.get_field("cadence"))
            .add_dependencies(
                {
                    Dependency.observation_type.value: [ObservationType.EXPERT],
                    Dependency.scheduling.value: [
                        SchedulingType.SCHEDULE.name,
                        SchedulingType.SCHEDULE_TIME.name,
                    ],
                }
            )
            .add_attrs({"placeholder": "default value"})
        )

        exp_start_end_observation = TURMDateTimeDuration(
            (
                ExpertObservation._meta.get_field("start_observation"),
                "Start Observation",
            ),
            (ExpertObservation._meta.get_field("end_observation"), "End Observation"),
        ).add_dependencies(
            {
                Dependency.observation_type.value: [
                    ObservationType.EXPERT,
                ],
                Dependency.scheduling.value: [SchedulingType.TIMED.name],
            }
        )

        exp_minimum_altitude = (
            TURMField.init_from_model(
                ExpertObservation._meta.get_field("minimum_altitude")
            )
            .add_dependencies(
                {
                    Dependency.observation_type.value: [
                        ObservationType.EXPERT,
                    ]
                }
            )
            .add_attrs({"placeholder": "default value"})
        )
        exp_minimum_altitude.required = False

        moon_separation_settings = [
            (
                TURMField.model_field_to_input(
                    ExpertObservation._meta.get_field("moon_separation_angle")
                ).add_attrs({"placeholder": "default value"}),
                "Moon Separation Angle",
            ),
            (
                TURMField.model_field_to_input(
                    ExpertObservation._meta.get_field("moon_separation_width")
                ).add_attrs({"placeholder": "default value"}),
                "Moon Separation Width",
            ),
        ]

        moon_separation = TURMGridField(
            moon_separation_settings, (2, 1)
        ).add_dependencies(
            {Dependency.observation_type.value: [ObservationType.EXPERT]}
        )
        moon_separation.required = False
        priority = (
            TURMField.init_from_model(ExpertObservation._meta.get_field("priority"))
            .add_dependencies(
                {Dependency.observation_type.value: [ObservationType.EXPERT]}
            )
            .add_attrs({"placeholder": "default value"})
        )
        priority.required = False
    except ProgrammingError as error:
        error_message = str(error).split("\n")[0]
        logger.warning(f"DB seems to be badly configured. \n{error_message}")

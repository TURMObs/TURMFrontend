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


class CelestialTargetForm(forms.Form):
    name = TURMField.init_from_model(CelestialTarget._meta.get_field("name")).add_attrs(
        {"placeholder": "OrionNebula"}
    )
    target_widgets = [
        (TURMCharInput("catalog_id"), "Catalog ID"),
        (TURMButtonInput("Fetch SIMBAD coordinates", "fetch_coordinates()"), ""),
    ]
    catalog_id = TURMGridField(target_widgets, (2, 1))
    ra = TURMField.init_from_model(CelestialTarget._meta.get_field("ra")).add_attrs(
        {"placeholder": "hh mm ss"}
    )
    dec = TURMField.init_from_model(CelestialTarget._meta.get_field("dec")).add_attrs(
        {"placeholder": "dd mm ss"}
    )


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
            model_field=AbstractObservation._meta.get_field("observatory")
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
        exposure_time_expert = TURMField.init_from_model(
            AbstractObservation._meta.get_field("exposure_time"),
            label_name="Exposure Time",
        ).add_dependencies(
            {Dependency.observation_type.value: [ObservationType.EXPERT]}
        )

        # exposure
        exposure_settings = [
            (
                ExpertObservation._meta.get_field("frames_per_filter"),
                "Frames per filter",
            ),
            (ExpertObservation._meta.get_field("dither_every"), "dither every"),
            (ExposureSettings._meta.get_field("binning"), "binning"),
            (ExposureSettings._meta.get_field("subFrame"), "sub frame"),
            (ExposureSettings._meta.get_field("gain"), "gain"),
            (ExposureSettings._meta.get_field("offset"), "offset"),
        ]

        exposure = TURMGridField.init_from_model(
            exposure_settings, (2, 3)
        ).add_dependencies(
            {Dependency.observation_type.value: [ObservationType.EXPERT]}
        )
        # imaging
        frames_per_filter = TURMField.init_from_model(
            ExpertObservation._meta.get_field("frames_per_filter")
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
                    ObservationType.EXPERT,
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
                    ObservationType.EXPERT,
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
                    ObservationType.EXPERT,
                ]
            }
        )

        cadence = TURMField.init_from_model(
            ExpertObservation._meta.get_field("cadence")
        ).add_dependencies(
            {
                Dependency.observation_type.value: [
                    ObservationType.MONITORING,
                    ObservationType.EXPERT,
                ]
            }
        )
        moon_separation_settings = [
            (
                ExpertObservation._meta.get_field("moon_separation_angle"),
                "Moon Separation Angle",
            ),
            (
                ExpertObservation._meta.get_field("moon_separation_width"),
                "Moon Separation Width",
            ),
        ]

        moon_separation = TURMGridField.init_from_model(
            moon_separation_settings, (2, 1)
        ).add_dependencies(
            {Dependency.observation_type.value: [ObservationType.EXPERT]}
        )
        priority = TURMField.init_from_model(
            ExpertObservation._meta.get_field("priority")
        ).add_dependencies(
            {Dependency.observation_type.value: [ObservationType.EXPERT]}
        )
    except ProgrammingError as error:
        error_message = str(error).split("\n")[0]
        logger.warning(f"DB seems to be badly configured. \n{error_message}")

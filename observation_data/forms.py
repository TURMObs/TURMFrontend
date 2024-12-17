from datetime import date, datetime
from enum import Enum

from django import forms
from django.forms import DateInput
from django.forms.widgets import DateTimeInput

from observation_request.TURMField import TURMModelField, TURMGridField, TURMField, TURMRadioInput
from observation_request.widgets import TURMCheckboxSelectWidget, TURMNumericInputWidget
from .models import (
    CelestialTarget,
    ExpertObservation,
    ObservationType,
    Filter,
    Observatory, ImagingObservation, AbstractObservation, ExoplanetObservation, VariableObservation,
    MonitoringObservation, ExposureSettings,
)


def observatory_dependency_attribute_factory(filter):
    out = ""
    for observatory in Observatory.objects.filter(
        filter_set__filter_type__icontains=filter
    ).iterator():
        out += f'data-{observatory}="True"'
    return out


class QueryEnum(Enum):
    observation_type_dependent = "observation_type_dependent"
    observatory_dependent = "observatory_dependent"


class ProjectForm(forms.ModelForm):
    class Meta:
        model = ExpertObservation
        fields = ["observatory"]

    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({"class": "input_text"})

class WipForm(forms.Form):
    required_amount = forms.CharField()
    def __init__(self, *args, **kwargs):
        super(WipForm, self).__init__(*args, **kwargs)
        #super(, self).__init__(*args, **kwargs)
        self.fields["required_amount"].widget = TURMNumericInputWidget(
            minimum=0, maximum=100, step=1, numeric_type="integer"
        )
        self.fields["required_amount"].widget.attrs.update({"class": "input_text observation_type_dependent",
                                                            "data-imaging": "true",
                                                            "data-variable": "true",
                                                            "data-monitor": "true",
                                                            "data-expert": "true"})
        widget = self.fields["required_amount"].widget

class CelestialTargetForm(forms.ModelForm):
    class Meta:
        model = CelestialTarget
        fields = ["name", "catalog_id","ra", "dec"]

    def __init__(self, *args, **kwargs):
        super(CelestialTargetForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({"class": "input_text"})
        self.fields["name"].widget.attrs.update({"placeholder": "OrionNebula"})
        self.fields["catalog_id"].widget.attrs.update({"placeholder": "M42"})
        self.fields["ra"].widget.attrs.update({"placeholder": "hh mm ss"})
        self.fields["dec"].widget.attrs.update({"placeholder": "dd mm ss"})


class ExposureForm(forms.ModelForm):
    class Meta:
        model = ExpertObservation
        fields = [
            "filter_set",
            "exposure_time",
            "frames_per_filter",
            "dither_every",
            "binning",
            # "sub_frame",
            # "gain",
            # "offset"
            "start_observation",
            "end_observation",
            "start_scheduling",
            "end_scheduling",
            "cadence",
            "moon_separation_angle",
            "moon_separation_width",
            "minimum_altitude",
        ]

    def __init__(self, *args, **kwargs):
        super(ExposureForm, self).__init__(*args, **kwargs)

        self.fields["exposure_time"].widget = TURMNumericInputWidget(
            minimum=0, maximum=100, step=0.01, numeric_type="integer"
        )  # todo 30, 60, 120, 300 sec, im expert frei

        self.fields["frames_per_filter"].widget = TURMNumericInputWidget(
            minimum=1, maximum=1_000, step=1, numeric_type="integer"
        )

        for field in ["start_observation", "end_observation"]:
            self.fields[field].widget = DateTimeInput(
                attrs={
                    "min": datetime.now().strftime("%Y-%d-%mT%H:%M"),
                    "type": "datetime-local",
                }
            )

        self.fields["minimum_altitude"].widget = TURMNumericInputWidget(
            minimum=0, maximum=60, step=1, numeric_type="integer"
        )

        self.fields["cadence"].widget = TURMNumericInputWidget(
            minimum=1, maximum=14, step=1, numeric_type="integer"
        )

        for field in ["start_scheduling", "end_scheduling"]:
            self.fields[field].widget = DateInput(
                attrs={"min": date.today(), "type": "date"}
            )

        # integer inputs zero or greater
        for field in ["frames_per_filter", "minimum_altitude"]:
            self.fields[field].widget = TURMNumericInputWidget(
                minimum=0, maximum=100, step=1, numeric_type="integer"
            )

        for field in self.fields:
            self.fields[field].widget.attrs.update({"class": "input_text"})

        # All
        self.label_widgets(
            self.fields,
            ObservationType.EXPERT,
            QueryEnum.observation_type_dependent.name,
        )
        # Imaging
        self.label_widgets(
            ["filter_set", "exposure_time", "frames_per_filter"],
            ObservationType.IMAGING,
            QueryEnum.observation_type_dependent.name,
        )
        # Exoplanet
        self.label_widgets(
            ["filter_set", "exposure_time", "start_observation", "end_observation"],
            ObservationType.EXOPLANET,
            QueryEnum.observation_type_dependent.name,
        )
        # Variable
        self.label_widgets(
            ["filter_set", "exposure_time", "minimum_altitude"],
            ObservationType.VARIABLE,
            QueryEnum.observation_type_dependent.name,
        )
        # Monitoring
        self.label_widgets(
            [
                "filter_set",
                "exposure_time",
                "frames_per_filter",
                "start_scheduling",
                "end_scheduling",
                "cadence",
            ],
            ObservationType.MONITORING,
            QueryEnum.observation_type_dependent.name,
        )

        # filter set
        self.fields["filter_set"] = forms.Field(
            widget=TURMCheckboxSelectWidget(
                queryset=Filter.objects.all(),
                extra_attribute_factory=observatory_dependency_attribute_factory,
                tooltip="selected Observatory does not support this filter",
            )
        )
        self.fields["filter_set"].widget.attrs.update(
            {"class": QueryEnum.observatory_dependent.name}
        )

    def label_widgets(self, fields, attr, html_class: str):
        for field in fields:
            widget = self.fields[field].widget

            if "class" in widget.attrs:
                prior = widget.attrs["class"]
                if html_class not in prior:
                    widget.attrs.update({"class": f"{prior} {html_class}"})
            else:
                widget.attrs.update({"class": html_class})

            widget.attrs.update({f"data-{attr}": "True"})


class TRUMProjectForm(forms.Form):
    observatory = TURMModelField(AbstractObservation._meta.get_field("observatory"))

def filter_set_dependency_generator(filter):
    dependency = {"observatory_dependant": []}
    for observatory in Observatory.objects.filter(filter_set__filter_type__icontains=filter).iterator():
        dependency["observatory_dependant"].append(str(observatory))
    print(dependency)
    return dependency

class ExposureSettingsForm(forms.Form):
    #
    observation_type_dependant = "observation_type_dependent"
    # combined
    filter_set = TURMModelField(ExpertObservation._meta.get_field("filter_set"), dependency_generator=filter_set_dependency_generator)


    exposure_time = TURMField(TURMRadioInput(name="exposure_time", choices=['15s', '30s', '60s', '120s', f'300s']),
                              label_name="exposure_time", dependencies=[
            ObservationType.IMAGING, ObservationType.EXOPLANET, ObservationType.VARIABLE])
    exposure_time_expert = TURMModelField(AbstractObservation._meta.get_field("exposure_time"),
                                          dependencies={"observation_type_dependent": [ObservationType.IMAGING,
                                                                                       ObservationType.EXOPLANET,
                                                                                       ObservationType.VARIABLE]})

    # exposure
    exposure_settings = [
        ExpertObservation._meta.get_field("frames_per_filter"),
        ExpertObservation._meta.get_field("dither_every"),
        ExposureSettings._meta.get_field("binning"),
        ExposureSettings._meta.get_field("subFrame"),
        ExposureSettings._meta.get_field("gain"),
        ExposureSettings._meta.get_field("offset"),
    ]
    exposure = TURMGridField(exposure_settings, (2, 3))

    # imaging
    frames_per_filter = TURMModelField(ExpertObservation._meta.get_field("frames_per_filter"))

    # exoplanet
    # start_observation = TURMModelField(ExpertObservation._meta.get_field("start_observation"))
    # end_observation =  TURMModelField(ExpertObservation._meta.get_field("end_observation"))

    # variable
    minimum_altitude = TURMModelField(ExpertObservation._meta.get_field("minimum_altitude"))

    # monitoring
    # start_scheduling = TURMModelField(ExpertObservation._meta.get_field("start_scheduling"))
    # end_scheduling = TURMModelField(ExpertObservation._meta.get_field("end_scheduling"))
    cadence = TURMModelField(ExpertObservation._meta.get_field("cadence"))


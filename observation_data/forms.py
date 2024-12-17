from datetime import date, datetime
from enum import Enum

from django import forms
from django.forms import DateInput
from django.forms.widgets import DateTimeInput

from observation_request.TURMField import TURMModelField, TURMGridField, TURMField, TURMRadioInput, TURMSelectField
from .models import (
    CelestialTarget,
    ExpertObservation,
    ObservationType,
    Observatory, AbstractObservation, ExposureSettings,
)


class Dependency(Enum):
    observation_type = "observation_type_dependent"
    observatory = "observatory_dependent"

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

class TRUMProjectForm(forms.Form):
    observatory = TURMModelField(AbstractObservation._meta.get_field("observatory"))

def filter_set_dependency_generator(filter):
    dependency = {Dependency.observatory.value: []}
    for observatory in Observatory.objects.filter(filter_set__filter_type__icontains=filter).iterator():
        dependency[Dependency.observatory.value].append(str(observatory))
    print(dependency)
    return dependency

class ExposureSettingsForm(forms.Form):
    observation_type = (TURMSelectField("observation_type", [o_type[1] for o_type in ObservationType.choices]) #{}
                        .add_on_click(lambda o_type : f"hide_inputs('{Dependency.observation_type.value}','{o_type}')"))
    # combined
    filter_set = (TURMModelField(ExpertObservation._meta.get_field("filter_set"))
                  .add_dependency_generator(filter_set_dependency_generator))


    exposure_time = TURMField(TURMRadioInput(name="exposure_time", choices=['15s', '30s', '60s', '120s', f'300s']),
                              label_name="exposure_time").add_dependencies(
        {Dependency.observation_type.value: [ObservationType.IMAGING, ObservationType.EXOPLANET, ObservationType.VARIABLE]})
    exposure_time_expert = TURMModelField(AbstractObservation._meta.get_field("exposure_time")).add_dependencies(
        {Dependency.observation_type.value: [ObservationType.EXPERT]})

    # exposure
    exposure_settings = [
        ExpertObservation._meta.get_field("frames_per_filter"),
        ExpertObservation._meta.get_field("dither_every"),
        ExposureSettings._meta.get_field("binning"),
        ExposureSettings._meta.get_field("subFrame"),
        ExposureSettings._meta.get_field("gain"),
        ExposureSettings._meta.get_field("offset"),
    ]
    exposure = TURMGridField(exposure_settings, (2, 3)).add_dependencies({Dependency.observation_type.value:
                                                                              [ObservationType.EXPERT]})

    # imaging
    frames_per_filter = TURMModelField(ExpertObservation._meta.get_field("frames_per_filter")).add_dependencies({
        Dependency.observation_type.value:
            [ObservationType.IMAGING]})

    # exoplanet
    # start_observation = TURMModelField(ExpertObservation._meta.get_field("start_observation"))
    # end_observation =  TURMModelField(ExpertObservation._meta.get_field("end_observation"))

    # variable
    minimum_altitude = TURMModelField(ExpertObservation._meta.get_field("minimum_altitude"))

    # monitoring
    # start_scheduling = TURMModelField(ExpertObservation._meta.get_field("start_scheduling"))
    # end_scheduling = TURMModelField(ExpertObservation._meta.get_field("end_scheduling"))
    cadence = TURMModelField(ExpertObservation._meta.get_field("cadence"))


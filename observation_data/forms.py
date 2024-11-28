from django import forms

from .models import (
    CelestialTarget,
    ExpertObservation,
    ObservationType,
)


class ProjectForm(forms.ModelForm):
    class Meta:
        model = ExpertObservation
        fields = ["observatory"]

    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({"class": "input_text"})


class CelestialTargetForm(forms.ModelForm):
    class Meta:
        model = CelestialTarget
        fields = ["name", "ra", "dec"]

    def __init__(self, *args, **kwargs):
        super(CelestialTargetForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({"class": "input_text"})
        self.fields["name"].widget.attrs.update({"placeholder": "M42"})
        self.fields["ra"].widget.attrs.update({"placeholder": "hh mm ss"})
        self.fields["dec"].widget.attrs.update({"placeholder": "dd mm ss"})


class ExposureForm(forms.ModelForm):
    class Meta:
        model = ExpertObservation
        fields = [
            "filter_set",
            "exposure_time",
            "frames_per_filter",
            "start_observation",
            "end_observation",
            "minimum_altitude",
            "cadence",
            "start_scheduling",
            "end_scheduling",
            "created_at",
        ]

    def __init__(self, *args, **kwargs):
        super(ExposureForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({"class": "input_text Expert"})

        # Imaging
        self.label_widgets(
            ["filter_set", "exposure_time", "frames_per_filter"],
            ObservationType.IMAGING,
        )
        # Exoplanet
        self.label_widgets(
            ["filter_set", "exposure_time", "start_observation", "end_observation"],
            ObservationType.EXOPLANET,
        )
        # Variable
        self.label_widgets(
            ["filter_set", "exposure_time", "minimum_altitude"],
            ObservationType.VARIABLE,
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
        )

    def label_widgets(self, fields, html_class):
        for field in fields:
            widget = self.fields[field].widget
            prior = widget.attrs["class"]
            widget.attrs.update({"class": f"{prior} {html_class}"})

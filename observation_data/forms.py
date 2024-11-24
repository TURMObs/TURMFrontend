from django import forms
from rest_framework.templatetags.rest_framework import add_class

from .models import CelestialTarget, ExoplanetObservation, ExpertObservation, AbstractObservation

class ProjectForm (forms.ModelForm):
    class Meta:
        model = ExpertObservation
        fields = ['observatory']


    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'input_text'})
            self.initial[field] = '0'



class CelestialTargetForm (forms.ModelForm):
    class Meta:
        model = CelestialTarget
        fields = ['name', 'catalog_id', 'ra', 'dec']

    def __init__(self, *args, **kwargs):
        super(CelestialTargetForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class':'input_text'})

class ExposureForm (forms.ModelForm):
    class Meta:
        model = ExpertObservation
        fields = ['filter_set', 'exposure_time', 'frames_per_filter', 'start_observation', 'end_observation', 'minimum_altitude', 'cadence', 'start_scheduling', 'end_scheduling', 'created_at',]


    def __init__(self, *args, **kwargs):
        super(ExposureForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'input_text Expert'})
            self.initial[field] = '0'

        # Imaging
        self.label_widgets(['filter_set', 'exposure_time', 'frames_per_filter'], AbstractObservation.ObservationType.IMAGING)
        # Exoplanet
        self.label_widgets(['filter_set', 'exposure_time', 'start_observation', 'end_observation'], AbstractObservation.ObservationType.EXOPLANET)
        # Exoplanet
        self.label_widgets(['filter_set', 'exposure_time', 'start_observation', 'end_observation'],
                           AbstractObservation.ObservationType.EXOPLANET)




    def label_widgets(self, fields, html_class):
        for field in fields:
            widget = self.fields[field].widget
            prior = widget.attrs['class']
            widget.attrs.update({'class': f"{prior} {html_class}"})

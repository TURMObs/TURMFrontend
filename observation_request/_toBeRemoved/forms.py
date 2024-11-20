from django import forms

from observations.models import *

class ExoplanetObservationForm(forms.ModelForm):

    class Meta:
        model = ExoplanetObservation
        fields = ['filter_set', 'observatory']

    def __init__(self, *args, **kwargs):
        super(ExoplanetObservationForm, self).__init__(*args, **kwargs)
        self.fields['observatory'].widget.attrs.update({'class':'input_text'})
        self.fields['filter_set'].widget.attrs.update({'class':'input_text'})

class CelestialTargetForm(forms.ModelForm):
    class Meta:
        model = CelestialTarget
        fields = ['name', 'coordinates']


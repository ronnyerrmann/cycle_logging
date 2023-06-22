from django import forms

from my_base import Logging

logger = Logging.setup_logger(__name__)


class PlotDataForm(forms.Form):
    CHOICES = (('date', 'Date'), ('km', 'Distance'), ('seconds', 'Duration'), ('kmh', 'Speed'))
    # initial= is defined by self.request.GET
    x_data = forms.ChoiceField(label="Plot on x-Axis:", choices=CHOICES)
    y_data = forms.ChoiceField(label="Plot on y-Axis:", choices=CHOICES)
    z_data = forms.ChoiceField(label="Plot on z-Axis:", choices=CHOICES+(('none', 'None'),))


class PlotDataFormSummary(forms.Form):
    CHOICES = (('date', 'Date'), ('km', 'Distance'), ('seconds', 'Duration'), ('kmh', 'Speed'), ('days', 'Days'))
    x_data = forms.ChoiceField(label="Plot on x-Axis:", choices=CHOICES)
    y_data = forms.ChoiceField(label="Plot on y-Axis:", choices=CHOICES)
    z_data = forms.ChoiceField(label="Plot on z-Axis:", choices=CHOICES+(('none', 'None'),))

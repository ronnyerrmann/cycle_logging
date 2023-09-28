from django import forms

from my_base import Logging

logger = Logging.setup_logger(__name__)


class PlotDataForm(forms.Form):
    CHOICES = (('date', 'Date'), ('distance', 'Distance'), ('duration', 'Duration'), ('speed', 'Speed'))
    # initial= is defined by self.request.GET
    x_data = forms.ChoiceField(label="Plot on x-Axis:", choices=CHOICES)
    y_data = forms.ChoiceField(label="Plot on y-Axis:", choices=CHOICES)
    z_data = forms.ChoiceField(label="Plot on z-Axis:", choices=CHOICES+(('none', 'None'),))


class PlotDataFormSummary(forms.Form):
    CHOICES = (('date', 'Date'), ('distance', 'Distance'), ('duration', 'Duration'), ('speed', 'Speed'),
               ('numberofdays', 'Days'))
    x_data = forms.ChoiceField(label="Plot on x-Axis:", choices=CHOICES)
    y_data = forms.ChoiceField(label="Plot on y-Axis:", choices=CHOICES)
    z_data = forms.ChoiceField(label="Plot on z-Axis:", choices=CHOICES+(('none', 'None'),))


class GpsDateRangeForm(forms.Form):
    begin_date = forms.DateField(
        label='Beginning Date',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    end_date = forms.DateField(
        label='End Date',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

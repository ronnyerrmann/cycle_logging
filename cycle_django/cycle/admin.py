from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import FahrradRides, FahrradWeeklySummary, FahrradMonthlySummary, FahrradYearlySummary, TimeInSecondsField


class AdminForm(forms.ModelForm):

    def clean(self):
        cleaned_data = super().clean()
        # Check that the speed makes sense
        date = cleaned_data.get('date')
        daykm = cleaned_data.get('daykm')
        dayseconds = int(cleaned_data.get('dayseconds').total_seconds())
        totalkm = cleaned_data.get('totalkm')
        totalseconds = int(cleaned_data.get('totalseconds').total_seconds())
        speed = daykm / dayseconds * 3600   # in km/h

        if speed < 2 or speed > 30:
            raise ValidationError(f"A speed of {speed:4.2f} km/h is outside the sensible range")

        previous = FahrradRides.objects.filter(date__lt=date).order_by('-date').first()

        if previous:
            if abs(previous.totalkm + daykm - totalkm) >= 1:
                # Avoid typing mistakes in day or total distance by checking that it differs less than 1 km
                raise ValidationError(
                    f"The current total ({totalkm}) differs from the sum of the last total "
                    f"({previous.totalkm}) plus current ({daykm}) [={previous.totalkm+daykm} km]"
                )

            prev_totalseconds = TimeInSecondsField.to_python(previous.totalseconds)
            if abs(prev_totalseconds + dayseconds - totalseconds) >= 60:
                # Avoid typing mistakes in day or total time by checking that is less than a minute
                raise ValidationError(
                    f"The current total ({TimeInSecondsField.convert_sec_to_str(totalseconds)}) differs from the sum "
                    f"of the last total ({TimeInSecondsField.convert_sec_to_str(prev_totalseconds)}) plus current "
                    f"({TimeInSecondsField.convert_sec_to_str(dayseconds)}) "
                    f"[={TimeInSecondsField.convert_sec_to_str(prev_totalseconds + dayseconds)}]"
                )

        return cleaned_data


@admin.register(FahrradRides)
class FahrradRidesAdmin(admin.ModelAdmin):
    form = AdminForm
    list_display = (
        'date', 'daykm', 'dayseconds', 'daykmh', 'totalkm', 'totalseconds', 'totalkmh', 'culmkm', 'culmseconds'
    )    # make it into a nice list
    readonly_fields = ('culmkm', 'culmseconds')
    fieldsets = (
        (None, {
            'fields': ('date', 'daykm', 'dayseconds')
        }),
        ('Total', {
            'fields': ('totalkm', 'totalseconds')
        }),
        ('For database automatic process', {
            'fields': ('culmkm', 'culmseconds')
        }),

    )

    """def save_model(self, request, obj, form, change: bool):
        # Perform additional validation or modifications before saving
        # raise ValidationError here will interrup program execution
        # obj: current model object
        # change: True if the entry is modified
        super().save_model(request, obj, form, change)"""


@admin.register(FahrradWeeklySummary)
class FahrradWeeklySummaryAdmin(admin.ModelAdmin):
    list_display = ('week_starting_on', 'weekkm', 'weekseconds', 'weekkmh', 'weekdays')


@admin.register(FahrradMonthlySummary)
class FahrradMonthlySummaryAdmin(admin.ModelAdmin):
    list_display = ('month_starting_on', 'monthkm', 'monthseconds', 'monthkmh', 'monthdays')


#admin.site.register(FahrradYearlySummary)
class FahrradYearlySummaryAdmin(admin.ModelAdmin):
    list_display = ('year_starting_on', 'yearkm', 'yearseconds', 'yearkmh', 'yeardays')


# Register the admin class with the associated model
admin.site.register(FahrradYearlySummary, FahrradYearlySummaryAdmin)


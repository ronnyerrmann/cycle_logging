import copy

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import (
    CycleRides, CycleWeeklySummary, CycleMonthlySummary, CycleYearlySummary, GPSData, NoGoAreas, GeoLocateData,
    convert_to_str_hours
)

from my_base import Logging

logger = Logging.setup_logger(__name__)


class AdminForm(forms.ModelForm):

    def clean(self):
        cleaned_data = super().clean()
        # Check that the speed makes sense
        date = cleaned_data.get('date')
        distance = cleaned_data.get('distance')
        duration = cleaned_data.get('duration')
        totaldistance = cleaned_data.get('totaldistance')
        totalduration = cleaned_data.get('totalduration')
        if not (date and distance and duration and totaldistance and totalduration):
            raise ValidationError("Not all values were given")

        dayseconds = int(duration.total_seconds())
        totalseconds = int(totalduration.total_seconds())
        speed = distance / dayseconds * 3600   # in km/h

        if speed < 2 or speed > 30:
            raise ValidationError(f"A speed of {speed:4.2f} km/h is outside the sensible range")

        previous = CycleRides.objects.filter(date__lt=date).order_by('-date').first()

        if previous:
            if abs(previous.totaldistance + distance - totaldistance) >= 1:
                # Avoid typing mistakes in day or total distance by checking that it differs less than 1 km
                raise ValidationError(
                    f"The current total ({totaldistance}) differs from the sum of the last total "
                    f"({previous.totaldistance}) plus current ({distance}) [={previous.totaldistance+distance} km]"
                )

            prev_totalseconds = int(previous.totalduration.total_seconds())
            totalseconds_ori = copy.copy(totalseconds)
            for ii in range(2):
                if abs(prev_totalseconds + dayseconds - totalseconds) <= 60:
                    # Avoid typing mistakes in day or total time by checking that is less than a minute
                    if ii == 1:
                        cleaned_data["totalduration"] *= 60
                    break
                # check that the user just didn't forget to add :00 to the end
                totalseconds *= 60
            else:
                raise ValidationError(
                    f"The current total ({convert_to_str_hours(totalseconds_ori)}) differs from the "
                    f"sum of the last total ({convert_to_str_hours(prev_totalseconds)}) plus current "
                    f"({convert_to_str_hours(dayseconds)}) "
                    f"[={convert_to_str_hours(prev_totalseconds + dayseconds)}]"
                )

        return cleaned_data


@admin.register(CycleRides)
class CycleRidesAdmin(admin.ModelAdmin):
    form = AdminForm
    list_display = (
        'date', 'distance', 'duration', 'speed', 'totaldistance', 'totalduration', 'totalspeed', 'cumdistance', 'cumduration'
    )    # make it into a nice list
    readonly_fields = ('cumdistance', 'cumduration')
    fieldsets = (
        (None, {
            'fields': ('date', 'distance', 'duration')
        }),
        ('Total', {
            'fields': ('totaldistance', 'totalduration')
        }),
        ('For database automatic process', {
            'fields': ('cumdistance', 'cumduration')
        }),

    )

    def response_add(self, request, obj, post_url_continue=None):
        self.message_user(request, f"Average is {obj.speed} km/s.")

        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        self.message_user(request, f"Average is {obj.speed} km/s.")

        return super().response_change(request, obj)

    """def save_model(self, request, obj, form, change: bool):
        # Perform additional validation or modifications before saving
        # raise ValidationError here will interrup program execution
        # obj: current model object
        # change: True if the entry is modified
        super().save_model(request, obj, form, change)"""


@admin.register(CycleWeeklySummary)
class CycleWeeklySummaryAdmin(admin.ModelAdmin):
    list_display = ('date', 'distance', 'duration', 'speed', 'numberofdays')


@admin.register(CycleMonthlySummary)
class CycleMonthlySummaryAdmin(admin.ModelAdmin):
    list_display = ('date', 'distance', 'duration', 'speed', 'numberofdays')


#admin.site.register(CycleYearlySummary)
class CycleYearlySummaryAdmin(admin.ModelAdmin):
    list_display = ('date', 'distance', 'duration', 'speed', 'numberofdays')

# Register the admin class with the associated model instead of using a decorator
admin.site.register(CycleYearlySummary, CycleYearlySummaryAdmin)

@admin.register(GPSData)
class GPSDataAdmin(admin.ModelAdmin):
    pass


@admin.register(NoGoAreas)
class NoGoAreasAdmin(admin.ModelAdmin):
    pass

@admin.register(GeoLocateData)
class GeoLocateDataAdmin(admin.ModelAdmin):
    form = AdminForm
    list_display = (
        'name', 'radius', 'latitude', 'longitude'
    )



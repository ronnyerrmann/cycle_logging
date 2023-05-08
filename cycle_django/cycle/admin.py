from django.contrib import admin

from .models import FahrradRides, FahrradWeeklySummary, FahrradMonthlySummary, FahrradYearlySummary


@admin.register(FahrradRides)
class FahrradRidesAdmin(admin.ModelAdmin):

    list_display = (
        'date', 'daykm', 'dayseconds', 'daykmh', 'totalkm', 'totalseconds', 'totalkmh', 'culmkm', 'culmseconds'
    )    # make it into a nice list
    fieldsets = (
        (None, {
            'fields': ('date', 'daykm', 'dayseconds')
        }),
        ('Total', {
            'fields': ('totalkm', 'totalseconds')
        }),
        ('For database automatic process', {
            'fields': ('wasupdated', 'culmkm', 'culmseconds')
        }),

    )


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


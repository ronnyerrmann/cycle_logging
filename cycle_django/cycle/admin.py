from django.contrib import admin

from .models import FahrradRides, FahrradWeeklySummary, FahrradMonthlySummary, FahrradYearlySummary

#admin.site.register(FahrradRides)
@admin.register(FahrradRides)
class FahrradRidesAdmin(admin.ModelAdmin):
    list_display = ('date', 'daykm', 'display_sec_day', 'daykmh', 'totalkm', 'display_sec_total', 'totalkmh', 'culmkm', 'display_sec_culm')    # make it into a nice list

#admin.site.register(FahrradWeeklySummary)
@admin.register(FahrradWeeklySummary)
class FahrradWeeklySummaryAdmin(admin.ModelAdmin):
    list_display = ('week_starting_on', 'weekkm', 'display_sec', 'weekkmh', 'weekdays')

#admin.site.register(FahrradMonthlySummary)
# Register the Admin classes for Book using the decorator
@admin.register(FahrradMonthlySummary)
class FahrradMonthlySummaryAdmin(admin.ModelAdmin):
    list_display = ('month_starting_on', 'monthkm', 'display_sec', 'monthkmh', 'monthdays')

#admin.site.register(FahrradYearlySummary)
class FahrradYearlySummaryAdmin(admin.ModelAdmin):
    list_display = ('year_starting_on', 'yearkm', 'display_sec', 'yearkmh', 'yeardays')
# Register the admin class with the associated model
admin.site.register(FahrradYearlySummary, FahrradYearlySummaryAdmin)


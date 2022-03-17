from django.db import models
from django.urls import reverse
# using: python manage.py inspectdb > models.py

def convert_sec(seconds):
    return "{:02d}:{:02d}:{:02d}".format(int(seconds/3600), int(seconds/60)%60, seconds%60)

class FahrradRides(models.Model):
    entryid = models.AutoField(db_column='EntryID', primary_key=True, help_text='Will be filled automatically')  # Field name made lowercase.
    date = models.DateField(db_column='Date', help_text='Give the Date')  # Field name made lowercase.
    daykm = models.FloatField(db_column='DayKM', help_text='Give the Distance in KM')  # Field name made lowercase.
    dayseconds = models.IntegerField(db_column='DaySeconds', help_text='Give the Time in Seconds')  # Field name made lowercase.
    daykmh = models.FloatField(db_column='DayKMH', blank=True, null=True, help_text='Will be filled automatically')  # Field name made lowercase.
    totalkm = models.FloatField(db_column='TotalKM', unique=True, help_text='Give the Distance in KM')  # Field name made lowercase.
    totalseconds = models.IntegerField(db_column='TotalSeconds', help_text='Give the Time in Seconds')  # Field name made lowercase.
    totalkmh = models.FloatField(db_column='TotalKMH', blank=True, null=True, help_text='Will be filled automatically')  # Field name made lowercase.
    culmkm = models.FloatField(db_column='CulmKM', blank=True, null=True, help_text='Will be filled automatically')  # Field name made lowercase.
    culmseconds = models.IntegerField(db_column='CulmSeconds', blank=True, null=True, help_text='Will be filled automatically')  # Field name made lowercase.
    wasupdated = models.IntegerField(blank=True, null=True, help_text='Will be filled automatically when new')

    class Meta:
        managed = False     # Won't apply any changes to
        db_table = 'fahrrad_rides'
        unique_together = (('date', 'daykm', 'dayseconds'),)
        ordering = ['date']

    def get_absolute_url(self):
        """Returns the url to access a detail record for this day."""
        return reverse('cycle-detail', args=[str(self.entryid)])
   
    def display_sec_day(self):      # To show time instead of seconds in the Admin List view
        return convert_sec(self.dayseconds)
    display_sec_day.short_description = 'Time'
    def display_sec_total(self):      # To show time instead of seconds in the Admin List view
        return convert_sec(self.totalseconds)
    display_sec_total.short_description = 'Time'
    def display_sec_culm(self):      # To show time instead of seconds in the Admin List view
        return convert_sec(self.culmseconds)
    display_sec_culm.short_description = 'Time'
        
class FahrradMonthlySummary(models.Model):
    month_starting_on = models.DateField(db_column='Month_starting_on', primary_key=True)  # Field name made lowercase.
    monthkm = models.FloatField(db_column='MonthKM')  # Field name made lowercase.
    monthseconds = models.IntegerField(db_column='MonthSeconds')  # Field name made lowercase.
    monthkmh = models.FloatField(db_column='MonthKMH', blank=True, null=True)  # Field name made lowercase.
    monthdays = models.IntegerField(db_column='MonthDays', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'fahrrad_monthly_summary'
    def get_absolute_url(self):
        return reverse('cycle-detail', args=["m"+str(self.month_starting_on)])
    def display_sec(self):      # To show time instead of seconds in the Admin List view
        return convert_sec(self.monthseconds)
    display_sec.short_description = 'Time'

class FahrradWeeklySummary(models.Model):
    week_starting_on = models.DateField(db_column='Week_starting_on', primary_key=True)  # Field name made lowercase.
    weekkm = models.FloatField(db_column='WeekKM')  # Field name made lowercase.
    weekseconds = models.IntegerField(db_column='WeekSeconds')  # Field name made lowercase.
    weekkmh = models.FloatField(db_column='WeekKMH', blank=True, null=True)  # Field name made lowercase.
    weekdays = models.IntegerField(db_column='WeekDays', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'fahrrad_weekly_summary'
    def get_absolute_url(self):
        return reverse('cycle-detail', args=["w"+str(self.week_starting_on)])
    def display_sec(self):      # To show time instead of seconds in the Admin List view
        return convert_sec(self.weekseconds)
    display_sec.short_description = 'Time'

class FahrradYearlySummary(models.Model):
    year_starting_on = models.DateField(db_column='Year_starting_on', primary_key=True, help_text='First date of the year')  # Field name made lowercase.
    yearkm = models.FloatField(db_column='YearKM', help_text='Give the Distance in KM')  # Field name made lowercase.
    yearseconds = models.IntegerField(db_column='YearSeconds', help_text='Give the Time in Seconds')  # Field name made lowercase.
    yearkmh = models.FloatField(db_column='YearKMH', blank=True, null=True)  # Field name made lowercase.
    yeardays = models.IntegerField(db_column='YearDays', help_text='Give the number of days with exercise in that year')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'fahrrad_yearly_summary'
    def get_absolute_url(self):
        return reverse('cycle-detail', args=["y"+str(self.year_starting_on)])
    def display_sec(self):      # To show time instead of seconds in the Admin List view
        return convert_sec(self.yearseconds)
    display_sec.short_description = 'Time'

#class cycle_data(FahrradRides):
#    def __init__(self):
#        super().__init__()


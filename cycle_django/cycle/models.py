import datetime
from typing import Union

from django.db import models
from django.urls import reverse
from django.forms import DurationField
# using: python manage.py inspectdb > models.py

from my_base import Logging
from . import backup

logger = Logging.setup_logger(__name__)


class TimeInSecondsField(models.IntegerField):
    description = "Stores time duration in seconds, but shows as timedelta"

    def from_db_value(self, value: int, expression, connection):
        if value is not None:
            # return my_timedelta(seconds=value)       # this would create 185d:06:10:05 instead of
            return self.convert_sec_to_str(value)

    @staticmethod
    def to_python(value: Union[int, datetime.timedelta, str]) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            # Convert "4446:10:05" into a timedelta object
            data = [int(ii) for ii in (":0:0:" + value).rsplit(":", 3)[-3:]]
            value = datetime.timedelta(hours=data[-3], minutes=data[-2], seconds=data[-1])
        if isinstance(value, datetime.timedelta):
            return int(value.total_seconds())
        if value is None:
            return value

        raise ValueError(f"Expected a timedelta object, got {value.__class__.__name__}")

    def get_prep_value(self, value: datetime.timedelta):
        return self.to_python(value)

    def formfield(self, **kwargs):
        defaults = {"form_class": DurationField}
        defaults.update(kwargs)
        defaults.pop("widget", None)      # Remove the AdminIntegerFieldWidget as it can't display the time on the admin page
        return super().formfield(**defaults)

    @staticmethod
    def convert_sec_to_str(seconds: int) -> str:
        if not isinstance(seconds, int):
            raise ValueError(f"Got {seconds.__class__.__name__} instead of int")
        return "{:02d}:{:02d}:{:02d}".format(int(seconds / 3600), int(seconds / 60) % 60, seconds % 60)


class FahrradRides(models.Model):
    # most of the fieldnames are lower case of the db fieldnames
    entryid = models.AutoField(db_column='EntryID', primary_key=True, help_text='Will be filled automatically') 
    date = models.DateField(db_column='Date', help_text='Give the Date') 
    daykm = models.FloatField(db_column='DayKM', help_text='Give the Distance in KM')
    #dayseconds = models.IntegerField(db_column='DaySeconds', help_text='Give the Time in Seconds')
    dayseconds = TimeInSecondsField(db_column='DaySeconds', verbose_name="Duration", help_text='Give in [HH:]MM:SS')
    daykmh = models.FloatField(db_column='DayKMH', blank=True, null=True, help_text='Will be filled automatically')
    totalkm = models.FloatField(db_column='TotalKM', unique=True, help_text='Give the Distance in KM')
    totalseconds = TimeInSecondsField(
        db_column='TotalSeconds', verbose_name="Total Duration", help_text='Give in [H]HH:MM:SS'
    )
    totalkmh = models.FloatField(db_column='TotalKMH', blank=True, null=True, help_text='Will be filled automatically')
    culmkm = models.FloatField(db_column='CulmKM', blank=True, null=True, help_text='Will be filled automatically')
    culmseconds = TimeInSecondsField(
        db_column='CulmSeconds', verbose_name="Culminated Duration", blank=True, null=True,
        help_text='Will be filled automatically'
    )
    wasupdated = models.IntegerField(blank=True, null=True, help_text='Will be filled automatically when new')

    class Meta:
        managed = False     # no database table creation, modification, or deletion operations will be performed for
        # this model (as done in separate before worked on django)
        db_table = 'fahrrad_rides'
        unique_together = (('date', 'daykm', 'dayseconds'),)
        ordering = ['date']

    def get_absolute_url(self):
        """Returns the url to access a detail record for this day."""
        return reverse('cycle-detail', args=[str(self.entryid)])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        backup.backup_db()


class FahrradMonthlySummary(models.Model):
    month_starting_on = models.DateField(db_column='Month_starting_on', primary_key=True)
    monthkm = models.FloatField(db_column='MonthKM')
    monthseconds = TimeInSecondsField(db_column='MonthSeconds', verbose_name="Duration in month")
    monthkmh = models.FloatField(db_column='MonthKMH', blank=True, null=True)
    monthdays = models.IntegerField(db_column='MonthDays', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'fahrrad_monthly_summary'
        ordering = ['month_starting_on']

    def get_absolute_url(self):
        return reverse('cycle-detail', args=["m"+str(self.month_starting_on)])


class FahrradWeeklySummary(models.Model):
    week_starting_on = models.DateField(db_column='Week_starting_on', primary_key=True)
    weekkm = models.FloatField(db_column='WeekKM')
    weekseconds = TimeInSecondsField(db_column='WeekSeconds', verbose_name="Duration in week")
    weekkmh = models.FloatField(db_column='WeekKMH', blank=True, null=True)
    weekdays = models.IntegerField(db_column='WeekDays', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'fahrrad_weekly_summary'
        ordering = ['week_starting_on']

    def get_absolute_url(self):
        return reverse('cycle-detail', args=["w"+str(self.week_starting_on)])


class FahrradYearlySummary(models.Model):
    year_starting_on = models.DateField(
        db_column='Year_starting_on', primary_key=True, help_text='First date of the year'
    )
    yearkm = models.FloatField(db_column='YearKM', help_text='Give the Distance in KM')
    yearseconds = TimeInSecondsField(db_column='YearSeconds', verbose_name="Duration in year")
    yearkmh = models.FloatField(db_column='YearKMH', blank=True, null=True)
    yeardays = models.IntegerField(db_column='YearDays', help_text='Give the number of days with exercise in that year')

    class Meta:
        managed = False
        db_table = 'fahrrad_yearly_summary'
        ordering = ['year_starting_on']

    def get_absolute_url(self):
        return reverse('cycle-detail', args=["y"+str(self.year_starting_on)])

import datetime
from typing import Union

from django.db import models
from django.db.models import Q, Sum, Count
from django.urls import reverse
import django.utils.duration
# using: python manage.py inspectdb > models.py

from my_base import Logging
from .backup import Backup

logger = Logging.setup_logger(__name__)


def convert_to_str_hours(value: Union[int, datetime.timedelta]) -> str:
    if isinstance(value, datetime.timedelta):
        value = value.total_seconds()
    if isinstance(value, float):
        value = int(value)
    if isinstance(value, int):
        return "{:02d}:{:02d}:{:02d}".format(int(value / 3600), int(value / 60) % 60, value % 60)
    if value is None:
        return value
    # logger.error(f"seconds should be int, but are {type(value)}: {value} - {isinstance(value, float)}")
    raise ValueError(f"Got {value.__class__.__name__} instead of int or timedelta")


def _get_duration_components_no_days(duration):
    """ Monkey Patch: Instead of d hh:mm:ss use hhh:mm:ss"""
    days = duration.days
    seconds = duration.seconds
    microseconds = duration.microseconds

    minutes = seconds // 60
    seconds = seconds % 60

    hours = minutes // 60 + days * 24
    minutes = minutes % 60

    return 0, hours, minutes, seconds, microseconds


django.utils.duration._get_duration_components = _get_duration_components_no_days


class CycleRides(models.Model):
    # most of the fieldnames are lower case of the db fieldnames
    entryid = models.AutoField(primary_key=True, help_text='Will be filled automatically')
    date = models.DateField(help_text='Give the Date')
    distance = models.FloatField(help_text='Give the Distance in KM')
    duration = models.DurationField(verbose_name="Duration", help_text='Give in [HH:]MM:SS')
    speed = models.FloatField(blank=True, null=True, help_text='Will be filled automatically')
    totaldistance = models.FloatField(unique=True, help_text='Give the Distance in KM')
    totalduration = models.DurationField(verbose_name="Total Duration", help_text='Give in [H]HH:MM:SS')
    totalspeed = models.FloatField(blank=True, null=True, help_text='Will be filled automatically')
    cumdistance = models.FloatField(blank=True, null=True, help_text='Will be filled automatically')
    cumduration = models.DurationField(
        verbose_name="Culminated Duration", blank=True, null=True, help_text='Will be filled automatically'
    )

    class Meta:
        unique_together = (('date', 'distance', 'duration'),)
        ordering = ['date']

    def get_absolute_url(self):
        """Returns the url to access a detail record for this day."""
        return reverse('cycle-detail', args=[str(self.entryid)])

    def save(self, *args, no_more_modifications=False, no_backup=False, no_summary=False, **kwargs):

        if no_more_modifications:
            # Just run parent save for entries that don't need more modification
            super().save(*args, **kwargs)
            return

        # Add speeds before saving
        self.speed = round(self.distance / self.duration.total_seconds() * 3600, 4)
        self.totalspeed = round(self.totaldistance / self.totalduration.total_seconds() * 3600, 4)

        super().save(*args, **kwargs)

        if not no_backup:
            Backup().backup_db()

        if not no_summary:
            self.mark_summary_tables(self)

        self.update_cumulative_values()

    def update_cumulative_values(self):
        # Calculate cumulative values
        date_for_cum = self.date
        if self.pk:
            # Object already exists in the database, check for field changes
            original_obj = CycleRides.objects.get(pk=self.pk)
            date_for_cum = min(date_for_cum, original_obj.date)

        # Last object with a culm distance
        for obj in CycleRides.objects.filter(date__lt=date_for_cum).order_by('-date'):
            if obj.cumdistance and obj.cumduration:
                prev_cumdistance = obj.cumdistance
                prev_cumduration = obj.cumduration
                break
            else:
                date_for_cum = obj.date
        else:
            prev_cumdistance = 0
            prev_cumduration = datetime.timedelta(0)

        for obj in CycleRides.objects.filter(date__gte=date_for_cum).order_by('date'):
            prev_cumdistance += obj.distance
            prev_cumduration += obj.duration
            obj.cumdistance = round(prev_cumdistance, 4)
            obj.cumduration = prev_cumduration
            obj.save(no_more_modifications=True)
            logger.info(f"Updated cumulative values for entry {obj.pk}: {obj.date}")

    @staticmethod
    def mark_summary_tables(obj: Union["CycleRides", None], update_all=False):
        # Mark in the summary tables that dates were updated
        if update_all:
            dates_to_mark = CycleRides.objects.values_list("date", flat=True)
            logger.info("Mark all summary tables to be updated")
        else:
            dates_to_mark = [obj.date]
            if obj.pk:
                # Object already exists in the database, check for field changes
                original_obj = CycleRides.objects.get(pk=obj.pk)
                dates_to_mark.append(original_obj.date)

        begin_of_week = set([date - datetime.timedelta(days=date.weekday()) for date in dates_to_mark])
        begin_of_month = set([datetime.date(date.year, date.month, 1) for date in dates_to_mark])
        begin_of_year = set([datetime.date(date.year, 1, 1) for date in begin_of_month])
        for date in begin_of_week:
            try:
                obj = CycleWeeklySummary.objects.get(date=date)
            except CycleWeeklySummary.DoesNotExist:
                obj = CycleWeeklySummary(date=date)
            obj.updated = True
            obj.save()
        for date in begin_of_month:
            try:
                obj = CycleMonthlySummary.objects.get(date=date)
            except CycleMonthlySummary.DoesNotExist:
                obj = CycleMonthlySummary(date=date)
            obj.updated = True
            obj.save()
        for date in begin_of_year:
            try:
                obj = CycleYearlySummary.objects.get(date=date)
            except CycleYearlySummary.DoesNotExist:
                obj = CycleYearlySummary(date=date)
            obj.updated = True
            obj.save()


    @classmethod
    def load_data(cls):
        backup = Backup()
        loaded_backup = backup.load_backup()
        if CycleRides.objects.all().count() == 0:
            loaded_backup |= backup.load_backup_mysql_based()
        if loaded_backup:
            logger.info("Loaded data")
            # Update the summary tables if database dump or backup was loaded successfully
            cls.mark_summary_tables(None, update_all=True)


def update_fields_common(my_filter, obj):
    summary = CycleRides.objects.filter(my_filter).aggregate(
        distance=Sum("distance"),
        duration=Sum("duration"),
        numberofdays=Count("entryid")
    )
    obj.distance = round(summary["distance"], 4)
    obj.duration = summary["duration"]
    obj.speed = round(summary["distance"] / summary["duration"].total_seconds() * 3600, 4)
    obj.numberofdays = summary["numberofdays"]
    obj.updated = False
    obj.save()


class CycleWeeklySummary(models.Model):
    date = models.DateField(primary_key=True)
    distance = models.FloatField(null=True)
    duration = models.DurationField(verbose_name="Duration in week", null=True)
    speed = models.FloatField(blank=True, null=True)
    numberofdays = models.IntegerField(blank=True, null=True)
    updated = models.BooleanField(null=True)

    class Meta:
        ordering = ['date']

    def get_absolute_url(self):
        return reverse('cycle-detail', args=["w"+str(self.date)])

    @staticmethod
    def update_fields():
        for obj in CycleWeeklySummary.objects.filter(updated=True):
            my_filter = Q(date__gte=obj.date) & Q(date__lt=obj.date + datetime.timedelta(days=7))
            update_fields_common(my_filter, obj)


class CycleMonthlySummary(models.Model):
    date = models.DateField(primary_key=True)
    distance = models.FloatField(null=True)
    duration = models.DurationField(verbose_name="Duration in month", null=True)
    speed = models.FloatField(blank=True, null=True)
    numberofdays = models.IntegerField(blank=True, null=True)
    updated = models.BooleanField(null=True)

    class Meta:
        ordering = ['date']

    def get_absolute_url(self):
        return reverse('cycle-detail', args=["m"+str(self.date)])

    @staticmethod
    def update_fields():
        for obj in CycleMonthlySummary.objects.filter(updated=True):
            end_date = obj.date + datetime.timedelta(days=31)
            end_date -= datetime.timedelta(days=end_date.day - 1)
            my_filter = Q(date__gte=obj.date) & Q(date__lt=end_date)
            update_fields_common(my_filter, obj)


class CycleYearlySummary(models.Model):
    date = models.DateField(primary_key=True, help_text='First date of the year')
    distance = models.FloatField(null=True)
    duration = models.DurationField(verbose_name="Duration in year", null=True)
    speed = models.FloatField(blank=True, null=True)
    numberofdays = models.IntegerField(help_text='Give the number of days with exercise in that year', null=True)
    updated = models.BooleanField(null=True)

    class Meta:
        ordering = ['date']

    def get_absolute_url(self):
        return reverse('cycle-detail', args=["y"+str(self.date)])

    @staticmethod
    def update_fields():
        for obj in CycleYearlySummary.objects.filter(updated=True):
            end_date = datetime.date(obj.date.year+1, 1, 1)
            my_filter = Q(date__gte=obj.date) & Q(date__lt=end_date)
            update_fields_common(my_filter, obj)

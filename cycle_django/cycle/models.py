import datetime
from typing import Union

from django.db import models
from django.db.models import Q, Sum, Count
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

    def save(self, *args, no_more_modifications=False, no_backup=False, **kwargs):

        if no_more_modifications:
            # Just run parent save for entries that don't need more modification
            super().save(*args, **kwargs)
            return

        # Add speeds before saving
        self.speed = round(self.distance / self.duration.total_seconds() * 3600, 4)
        self.totalspeed = round(self.totaldistance / self.totalduration.total_seconds() * 3600, 4)

        super().save(*args, **kwargs)

        if not no_backup:
            backup.backup_db()

        self.mark_summary_tables()
        self.update_cumulative_values()

    def update_cumulative_values(self):
        # Calculate cumulative values
        date_for_cum = self.date
        if self.pk:
            # Object already exists in the database, check for field changes
            original_obj = FahrradRides.objects.get(pk=self.pk)
            date_for_cum = min(date_for_cum, original_obj.date)

        # Last object with a culm distance
        for obj in FahrradRides.objects.filter(date__lt=date_for_cum).order_by('-date'):
            if obj.cumdistance and obj.cumduration:
                prev_cumdistance = obj.cumdistance
                prev_cumduration = obj.cumduration
                break
            else:
                date_for_cum = obj.date
        else:
            prev_cumdistance = 0
            prev_cumduration = datetime.timedelta(0)

        for obj in FahrradRides.objects.filter(date__gte=date_for_cum).order_by('date'):
            prev_cumdistance += obj.distance
            prev_cumduration += obj.duration
            obj.cumdistance = round(prev_cumdistance, 4)
            obj.cumduration = prev_cumduration
            obj.save(no_more_modifications=True)
            logger.info(f"Updated cumulative values for entry {obj.pk}: {obj.date}")

    def mark_summary_tables(self):
        # Mark in the summary tables that dates were updated
        dates_to_mark = [self.date]
        if self.pk:
            # Object already exists in the database, check for field changes
            original_obj = FahrradRides.objects.get(pk=self.pk)
            dates_to_mark.append(original_obj.date)

        begin_of_week = set([date - datetime.timedelta(days=date.weekday()) for date in dates_to_mark])
        begin_of_month = set([datetime.date(date.year, date.month, 1) for date in dates_to_mark])
        begin_of_year = set([datetime.date(date.year, 1, 1) for date in begin_of_month])
        for date in begin_of_week:
            try:
                obj = FahrradWeeklySummary.objects.get(date=date)
            except FahrradWeeklySummary.DoesNotExist:
                obj = FahrradWeeklySummary(date=date)
            obj.updated = True
            obj.save()
        for date in begin_of_month:
            try:
                obj = FahrradMonthlySummary.objects.get(date=date)
            except FahrradMonthlySummary.DoesNotExist:
                obj = FahrradMonthlySummary(date=date)
            obj.updated = True
            obj.save()
        for date in begin_of_year:
            try:
                obj = FahrradYearlySummary.objects.get(date=date)
            except FahrradYearlySummary.DoesNotExist:
                obj = FahrradYearlySummary(date=date)
            obj.updated = True
            obj.save()


    @classmethod
    def load_data(cls):
        backup.load_backup()
        if FahrradRides.objects.all().count() == 0:
            backup.load_backup_mysql_based()
        logger.info("Loaded data")


def update_fields_common(my_filter, obj):
    summary = FahrradRides.objects.filter(my_filter).aggregate(
        distance=Sum("distance"),
        duration=Sum("duration"),
        numberofdays=Count("entryid")
    )
    obj.distance = summary["distance"]
    obj.duration = summary["duration"]
    obj.speed = round(summary["distance"] / summary["duration"].total_seconds() * 3600, 4)
    obj.numberofdays = summary["numberofdays"]
    obj.updated = False
    obj.save()


class FahrradWeeklySummary(models.Model):
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
        for obj in FahrradWeeklySummary.objects.filter(updated=True):
            my_filter = Q(date__gte=obj.date) & Q(date__lt=obj.date + datetime.timedelta(days=7))
            update_fields_common(my_filter, obj)


class FahrradMonthlySummary(models.Model):
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
        for obj in FahrradMonthlySummary.objects.filter(updated=True):
            end_date = obj.date + datetime.timedelta(days=31)
            end_date -= datetime.timedelta(days=end_date.day - 1)
            my_filter = Q(date__gte=obj.date) & Q(date__lt=end_date)
            update_fields_common(my_filter, obj)


class FahrradYearlySummary(models.Model):
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
        for obj in FahrradYearlySummary.objects.filter(updated=True):
            end_date = datetime.date(obj.date.year+1, 1, 1)
            my_filter = Q(date__gte=obj.date) & Q(date__lt=end_date)
            update_fields_common(my_filter, obj)

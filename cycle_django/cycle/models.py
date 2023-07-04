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

    def save(self, *args, no_more_modifications=False, **kwargs):

        if no_more_modifications:
            # Just run parent save for entries that don't need more modification
            super().save(*args, **kwargs)
            return

        # Add speeds before saving
        self.speed = round(self.distance / self.duration.total_seconds() * 3600, 4)
        self.totalspeed = round(self.totaldistance / self.totalduration.total_seconds() * 3600, 4)

        super().save(*args, **kwargs)

        backup.backup_db()

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
                logger.info(f"prev distance {prev_cumdistance}")
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
            obj.cumdistance = prev_cumdistance
            obj.cumduration = prev_cumduration
            obj.save(no_more_modifications=True)
            logger.info(f"Updated cumulative values for entry {obj.pk}: {obj.date}")

    @classmethod
    def load_data(cls):
        logger.info("Loaded data")


class FahrradWeeklySummary(models.Model):
    date = models.DateField(primary_key=True)
    distance = models.FloatField()
    duration = models.DurationField(verbose_name="Duration in week")
    speed = models.FloatField(blank=True, null=True)
    numberofdays = models.IntegerField(blank=True, null=True)

    class Meta:
        ordering = ['date']

    def get_absolute_url(self):
        return reverse('cycle-detail', args=["w"+str(self.date)])


class FahrradMonthlySummary(models.Model):
    date = models.DateField(primary_key=True)
    distance = models.FloatField()
    duration = models.DurationField(verbose_name="Duration in month")
    speed = models.FloatField(blank=True, null=True)
    numberofdays = models.IntegerField(blank=True, null=True)

    class Meta:
        ordering = ['date']

    def get_absolute_url(self):
        return reverse('cycle-detail', args=["m"+str(self.date)])


class FahrradYearlySummary(models.Model):
    date = models.DateField(primary_key=True, help_text='First date of the year')
    distance = models.FloatField()
    duration = models.DurationField(verbose_name="Duration in year")
    speed = models.FloatField(blank=True, null=True)
    numberofdays = models.IntegerField(help_text='Give the number of days with exercise in that year')

    class Meta:
        ordering = ['date']

    def get_absolute_url(self):
        return reverse('cycle-detail', args=["y"+str(self.date)])

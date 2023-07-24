import datetime
import gpxpy
import json
import os
from typing import List, Union

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
            Backup().backup_cycle_rides()

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
        loaded_backup = backup.load_dump_cycle_rides()
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


class GPSData(models.Model):
    filename = models.CharField(primary_key=True, max_length=100)
    start = models.DateTimeField()
    end = models.DateTimeField()
    datetimes = models.TextField()
    latitudes = models.TextField()
    longitudes = models.TextField()
    altitudes = models.TextField()
    speeds = models.TextField(null=True)
    GPX_FOLDERS = ["/home/ronny/Documents/gps-logger/"]

    class Meta:
        ordering = ['start']

    def __str__(self):
        return f"{self.filename} - {self.datetimes.count(',')+1}"

    def save(self, *args, no_backup=False, **kwargs):

        super().save(*args, **kwargs)
        if not no_backup:
            Backup().dump_gpsdata_dbs()

    @classmethod
    def load_data(cls):
        backup = Backup()
        backup.load_dump_GPSData()

        #cls.import_gpx_file_to_database(cls.GPX_FOLDERS)

    @staticmethod
    def import_gpx_file_to_database(gpx_folders: List[str]):
        # Get all gpxfiles that are not in the database
        for folder in gpx_folders:
            gpx_files = []
            for foldername, subfolders, filenames in os.walk(folder):
                gpx_files += [
                    (foldername, filename) for filename in filenames
                    if filename.endswith(".gpx") and not GPSData.objects.filter(filename=filename).exists()
                ]
        gpx_files = [gpx_files[0]]    # to remove later
        # Read the gpx files
        for ii, (foldername, filename) in enumerate(gpx_files):
            with open(os.path.join(foldername, filename), 'r') as gpx_file:
                gpx = gpxpy.parse(gpx_file)

                for track in gpx.tracks:
                    datetimes = []
                    latitudes = []
                    longitudes = []
                    altitudes = []
                    for segment in track.segments:
                        for point in segment.points:
                            if not datetimes:
                                start = point.time
                            datetimes.append(point.time.timestamp())
                            latitudes.append(point.latitude)
                            longitudes.append(point.longitude)
                            altitudes.append(point.elevation)
                    end = point.time

                obj = GPSData(
                    filename=filename, start=start, end=end, datetimes=json.dumps(datetimes),
                    latitudes=json.dumps(latitudes), longitudes=json.dumps(longitudes),
                    altitudes=json.dumps(altitudes),
                )
                obj.save(no_backup=(ii < len(gpx_files)-1))
                logger.info(f"Loaded {len(datetimes)} points from {filename}")

class NoGoAreas(models.Model):
    name = models.TextField(primary_key=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    radius = models.FloatField()
    auto_whole_world = "Auto whole world"

    def save(self, *args, no_more_modifications=False, no_backup=False, no_summary=False, **kwargs):

        super().save(*args, **kwargs)
        Backup().dump_no_go_areas_dbs()

    @classmethod
    def load_data(cls):
        try:
            NoGoAreas.objects.filter(pk=cls.auto_whole_world).delete()
        except NoGoAreas.DoesNotExist:
            pass
        backup = Backup()
        loaded_backup = backup.load_dump_no_go_areas()
        if NoGoAreas.objects.all().count() == 0:
            logger.warning(f"No no-go-area defined, hence will create one for the whole world")
            obj = NoGoAreas(name=cls.auto_whole_world, latitude=0., longitude=0, radius=40000.)
            obj.save()

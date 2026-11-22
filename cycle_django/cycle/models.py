import datetime
import gpxpy
import io
import json
import os
import pandas
from PIL import Image
import numpy as np
from typing import Union, Tuple

from django.conf import settings
from django.db import models, transaction
from django.db.models import Q, Sum, Count
from django.urls import reverse
import django.utils.duration
# using: python manage.py inspectdb > models.py

from my_base import Logging, create_timezone_object, photoStorage, GPX_FOLDERS, EARTH_RADIUS
from .backup import Backup

logger = Logging.setup_logger(__name__)
backup_instance = Backup()

# Make SRTM available
hasSrtm = False
if os.environ.get('SRTM1_DIR'):
    try:
        import srtm
        elevation_data_30m = srtm.Srtm1HeightMapCollection()
        elevation_data_90m = srtm.Srtm3HeightMapCollection()
        hasSrtm = True
    except OSError as e:
        logger.warning(f'Failed loading the SRTM data: {e}')
else:
    logger.warning('Not using SRTM!')

def convert_to_str_hours(value: Union[int, datetime.timedelta, None]) -> Union[str, None]:
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


def _get_duration_components_no_days(duration) -> Tuple[int, int, int, int, int]:
    """ Monkey Patch: Instead of 'd hh:mm:ss' use 'hhh:mm:ss'"""
    days = duration.days
    seconds = duration.seconds
    microseconds = duration.microseconds

    minutes = seconds // 60
    seconds = seconds % 60

    hours = minutes // 60 + days * 24
    minutes = minutes % 60

    return 0, hours, minutes, seconds, microseconds


# Patch the django function
django.utils.duration._get_duration_components = _get_duration_components_no_days


class Bicycles(models.Model):
    id = models.AutoField(primary_key=True, help_text='Will be filled automatically')
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)

    table_name = 'Bicycles'

    @staticmethod
    def add_bicycle_if_none():
        if Bicycles.objects.all().count() == 0:
            Bicycles(description='standard').save()

    def __str__(self):
        return self.description

    def backup(self):
        data_string = ""
        for obj in Bicycles.objects.all():
            data_string += f"{obj.description};{obj.notes}\n"

        backup_instance.backup_table(self.table_name, data_string.encode())

    def save(self, *args, no_check=False, **kwargs):
        if self.is_default:
            for obj in Bicycles.objects.filter(is_default=True):
                obj.is_default = False
                obj.save(no_check=True)
        super().save(*args, **kwargs)
        self.backup()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.backup()

    @classmethod
    def load_data(cls):
        backup_instance.load_database_dump(cls.table_name)


class CycleRides(models.Model):
    # most of the fieldnames are lower case of the db fieldnames
    entryid = models.AutoField(primary_key=True, help_text='Will be filled automatically')
    date = models.DateField(help_text='Give the Date')
    distance = models.FloatField(help_text='Give the Distance in KM')
    duration = models.DurationField(verbose_name="Duration", help_text='Give in [HH:]MM:SS')
    speed = models.FloatField(blank=True, null=True, help_text='Will be filled automatically')
    totaldistance = models.FloatField(unique=False, help_text='Give the Distance in KM')
    totalduration = models.DurationField(verbose_name="Total Duration", help_text='Give in [H]HH:MM:SS')
    totalspeed = models.FloatField(blank=True, null=True, help_text='Will be filled automatically')
    cumbicycledistance = models.FloatField(
        verbose_name="Cumulated Distance for this bicycle", blank=True, null=True,
        help_text='Will be filled automatically'
    )
    cumbicycleduration = models.DurationField(
        verbose_name="Cumulated Duration for this bicycle", blank=True, null=True,
        help_text='Will be filled automatically'
    )
    cumdistance = models.FloatField(
        verbose_name="Cumulated Distance over all bicycles", blank=True, null=True, help_text='Will be filled automatically'
    )
    cumduration = models.DurationField(
        verbose_name="Cumulated Duration over all bicycles", blank=True, null=True, help_text='Will be filled automatically'
    )
    cumspeed = models.FloatField(
        verbose_name="Cumulated Speed", blank=True, null=True, help_text='Will be filled automatically'
    )
    bicycle = models.ForeignKey(Bicycles, on_delete=models.PROTECT)

    table_name = 'CycleRides'

    class Meta:
        unique_together = (('date', 'distance', 'duration'),)
        ordering = ['date']

    def get_absolute_url(self):
        """Returns the url to access a detail record for this day."""
        return reverse('cycle-detail', args=[str(self.entryid)])

    def get_gps_objs(self):
        """Returns the url to access a gps plot"""
        date = create_timezone_object(self.date)
        objs = GPSTrack.objects.filter(
            start_time__lt=date+datetime.timedelta(days=1)-datetime.timedelta(seconds=1), end_time__gt=date
        ).order_by('start_time')
        return objs

    def get_gps_url(self):
        """Returns the url to access a gps plot"""
        data = []
        for obj in self.get_gps_objs():
            data.append([reverse('gps_detail', args=[obj.filename]), obj.filename.rsplit('.', 1)[0]])
        return data

    def backup(self, csv_update: bool = True):
        data_string = ""
        if csv_update:
            for obj in CycleRides.objects.all():
                data_string += (f"{obj.date.strftime('%Y-%m-%d')};{obj.distance};{convert_to_str_hours(obj.duration)};"
                                f"{obj.totaldistance};{convert_to_str_hours(obj.totalduration)};{obj.bicycle.id}\n")

        backup_instance.backup_table(self.table_name, data_string.encode(), csv_dump=csv_update)

    def save(self, *args, no_more_modifications=False, run_backup=True, run_summary=True, run_cumulative=True, **kwargs):

        if no_more_modifications:
            # Just run parent save for entries that don't need more modification
            super().save(*args, **kwargs)
            return

        # Add speeds before saving
        self.speed = round(self.distance / self.duration.total_seconds() * 3600, 4)
        self.totalspeed = round(self.totaldistance / self.totalduration.total_seconds() * 3600, 4)

        super().save(*args, **kwargs)

        if run_backup:
            self.backup()

        if run_summary:
            self.mark_summary_tables(self)

        if run_cumulative:
            self.update_cumulative_values()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.mark_summary_tables(self)
        self.update_cumulative_values()
        self.backup()

    def update_cumulative_values(self):
        # Calculate cumulative values
        date_for_cum = self.date
        if self.pk:
            # Object already exists in the database, check for field changes
            original_obj = CycleRides.objects.get(pk=self.pk)
            date_for_cum = min(date_for_cum, original_obj.date)

        # Last object with a cumulative distance (for the current bicycle)
        for obj in CycleRides.objects.filter(date__lt=date_for_cum, bicycle=self.bicycle).order_by('-date'):
            if obj.cumbicycledistance and obj.cumbicycleduration:
                prev_cumdistance = obj.cumbicycledistance
                prev_cumduration = obj.cumbicycleduration
                break
            else:
                date_for_cum = obj.date
        else:
            prev_cumdistance = 0.0
            prev_cumduration = datetime.timedelta(0)

        change = False
        for obj in CycleRides.objects.filter(date__gte=date_for_cum, bicycle=self.bicycle).order_by('date'):
            prev_cumdistance += obj.distance
            prev_cumduration += obj.duration
            obj.cumbicycledistance = round(prev_cumdistance, 4)
            obj.cumbicycleduration = prev_cumduration
            obj.save(no_more_modifications=True)
            change = True
            logger.info(f"Updated cumulative values for entry {obj.pk}: {obj.date} for bycle: {self.bicycle}")

        # Last object with a cumulative distance (for all)
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
            obj.cumspeed = round(obj.cumdistance / obj.cumduration.total_seconds() * 3600, 4)
            obj.save(no_more_modifications=True)
            change = True
            logger.info(f"Updated cumulative values for entry {obj.pk}: {obj.date} for all bicycles")

        if change:
            self.backup(csv_update=False)

    @staticmethod
    def mark_summary_tables(obj: Union["CycleRides", None], update_all: bool = False):
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
        loaded_backup = backup_instance.load_database_dump(cls.table_name)
        if CycleRides.objects.all().count() == 0:
            loaded_backup |= backup_instance.load_backup_mysql_based()
        filename_csv_import = 'insert_data.csv.gz' # load a file with manual entries, needs to be zipped
        if os.path.isfile(filename_csv_import):
            logger.info(f'Loading data from {filename_csv_import}')
            loaded_backup |= backup_instance.load_csv_data(filename_csv_import)
            os.rename(filename_csv_import, filename_csv_import.replace('.csv.gz', '_done.csv.gz'))
            logger.info(f'Loaded data from {filename_csv_import} and renamed file')
        if loaded_backup:
            # Calculate the cumulative values for all entries
            # Todo: can't run update_cumulative_values as that is not a class function, needs a better way (needs to be on earliest entry for each bicycle)
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

    def get_gps_objs(self):
        """Returns the url to access a gps plot"""
        date = create_timezone_object(self.date)
        objs = GPSTrack.objects.filter(
            start_time__lt=date+datetime.timedelta(days=7)-datetime.timedelta(seconds=1), end_time__gt=date
        ).order_by('start_time')
        return objs


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

    def get_gps_objs(self):
        """Returns the url to access a gps plot"""
        date = create_timezone_object(self.date)
        end_date = date + datetime.timedelta(days=31)
        end_date -= datetime.timedelta(days=end_date.day - 1)
        objs = GPSTrack.objects.filter(
            start_time__lt=end_date-datetime.timedelta(seconds=1), end_time__gt=date
        ).order_by('start_time')
        return objs

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

    def get_gps_objs(self):
        """Returns the url to access a gps plot"""
        date = create_timezone_object(self.date)
        end_date = datetime.date(date.year + 1, 1, 1)
        objs = GPSTrack.objects.filter(
            start_time__lt=end_date-datetime.timedelta(seconds=1), end_time__gt=date
        ).order_by('start_time')
        return objs


class GPSFilesToIgnore(models.Model):
    filename = models.CharField(primary_key=True, max_length=100)
    notes = models.TextField(blank=True)

    table_name = 'GPSFilesToIgnore'

    def backup(self):
        data_string = ""
        for obj in GPSFilesToIgnore.objects.all():
            data_string += f"{obj.filename};{obj.notes}\n"

        backup_instance.backup_table(self.table_name, data_string.encode())

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.backup()
        GPSData.objects.filter(filename=self.filename).delete()
        for track in GPSTrack.objects.filter(filename=self.filename):
            track.delete()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.backup()

    @classmethod
    def load_data(cls):
        backup_instance.load_database_dump(cls.table_name)


class GPSTrack(models.Model):
    filename = models.CharField(primary_key=True, max_length=100)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    number_entries = models.IntegerField()
    total_distance_m = models.IntegerField(help_text="Total distance in metres")

    table_name = 'GPSTrack'

    already_tried_files = []

    class Meta:
        ordering = ['start_time', 'end_time']

    def __str__(self):
        return f"{self.filename} - {self.number_entries}"

    def get_absolute_url(self):
        """Returns the url to access a detail record for this GPS file."""
        return reverse('gps_detail', args=[self.filename])

    @property
    def total_distance_km(self) -> float:
        return self.total_distance_m / 1000

    def backup(self):
        """ Dumps the tracks and their points. Dumping the points is slow, so only call this after an import
        (or deletion) has finished and not for every single track """
        backup_instance.backup_table(self.table_name, ''.encode(), csv_dump=False)
        backup_instance.backup_table(GPSPoint.table_name, ''.encode(), csv_dump=False)

    def save(self, *args, run_backup=True, **kwargs):
        super().save(*args, **kwargs)
        if run_backup:
            self.backup()

    def delete(self, *args, run_backup=True, **kwargs):
        super().delete(*args, **kwargs)   # deletes the points via on_delete=CASCADE
        if run_backup:
            self.backup()

    @classmethod
    def load_data(cls):
        # Tracks first, as the points reference them
        backup_instance.load_database_dump(cls.table_name)
        GPSPoint.load_data()
        cls.import_gpx_file_to_database()

    @staticmethod
    def get_srtm_elevation(latitude: float, longitude: float) -> Union[float, None]:
        """ Returns the SRTM elevation (np.nan if unknown) or None if the SRTM data can't be read """
        elevation_srtm = None
        for i, elevation_data_source in enumerate((elevation_data_30m, elevation_data_90m)):
            try:
                elevation_srtm = elevation_data_source.get_altitude(latitude=latitude, longitude=longitude)
            except srtm.exceptions.NoHeightMapDataException:
                if i == 1:
                    logger.warning('Cannot read srtm data')
                    return None
            except AssertionError as e:
                if str(e).startswith('Unexpected number of bytes found in'):
                    logger.warning(f'Problem with (zipped) htg file: {e}')
                    return None
                raise
            else:  # no exceptions, don't try second elevation_data_source
                break
        # SRTM data below 0 m has an underflow of the uint to values above 65000
        # SRTM data that could not be determined because of too steep landscape is set to 32768
        if elevation_srtm > 65000:
            return -1
        return elevation_srtm if elevation_srtm < 30000 else np.nan

    @classmethod
    def read_gpx_file(cls, path: str) -> Union[pandas.DataFrame, None]:
        """ Reads the points of a gpx file, returns None if the file can't be used """
        times, latitudes, longitudes, elevations, ele_srtm = [], [], [], [], []
        with open(path, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    if not point.time:
                        logger.warning(f"Point without timestamp in {path}: {point} - will ignore file")
                        return None
                    if abs(point.latitude) == 90:  # ignore dummy values
                        continue
                    elevation_srtm = np.nan
                    if hasSrtm:
                        elevation_srtm = cls.get_srtm_elevation(point.latitude, point.longitude)
                        if elevation_srtm is None:
                            logger.warning(f'Will not read the file {path}')
                            return None
                    timestamp = point.time
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
                    times.append(timestamp)
                    latitudes.append(point.latitude)
                    longitudes.append(point.longitude)
                    elevations.append(np.nan if point.elevation is None else point.elevation)
                    ele_srtm.append(elevation_srtm)

        return pandas.DataFrame({
            'Timestamp': times,
            'Times': np.array([tt.timestamp() for tt in times], dtype=np.int64),  # e.g. 1269530756
            'Latitude_deg': np.array(latitudes, dtype=np.float64),
            'Longitude_deg': np.array(longitudes, dtype=np.float64),
            'Elevation': np.array(elevations, dtype=np.float64),
            'Elevation_srtm': np.array(ele_srtm, dtype=np.float64),
        })

    @staticmethod
    def adjust_elevation(df: pandas.DataFrame) -> str:
        """ Some devices don't record the correct gps elevation: move the elevations to match SRTM """
        alt_diff = (df['Elevation_srtm'] - df['Elevation']).dropna()
        alt_diff = alt_diff[np.abs(alt_diff) < 200]
        if alt_diff.shape[0] > 50:
            alt_adjust = np.median(alt_diff)
            if abs(alt_adjust) >= 10:
                df['Elevation'] += alt_adjust
                return f', moved altitudes by {alt_adjust:.1f}m to match SRTM'
        return ''

    @staticmethod
    def calculate_track_values(df: pandas.DataFrame):
        """ Adds Duration (s), Distance (km) and Speed_5/Speed_50 (km/h) to the DataFrame.
        Duration/Distance of point i are relative to point i-1 and NaN during/after a pause.
        Be careful to apply sin/cos only on radians!
        """
        window_med_duration = 50
        paused_after = 30  # assume a pause if the next data point took 30s to appear
        min_consecutive_points = 10  # exclude sections with breaks within min_consecutive_points points
        min_periods = 3  # to calculate rolling median/sum at least these number of datapoints should not be nans

        latitude_rad = np.radians(df['Latitude_deg'])
        longitude_rad = np.radians(df['Longitude_deg'])
        sin_lat = np.sin(latitude_rad)
        cos_lat = np.cos(latitude_rad)

        # Duration
        duration = df['Times'].diff().to_numpy(dtype=np.float64)  # in seconds
        duration[0] = 0
        # Exclude datapoints after/during a stop
        duration[duration > paused_after] = np.nan
        duration_rolling_median = pandas.Series(duration).rolling(
            window=window_med_duration, min_periods=int(0.1 * window_med_duration)
        ).median().to_numpy()
        duration[duration > 3 * duration_rolling_median] = np.nan
        duration_is_nan = np.where(np.isnan(duration))[0]
        if duration_is_nan.shape[0] >= 1:
            if duration_is_nan[0] <= min_consecutive_points:
                duration[0:duration_is_nan[0]] = np.nan
            if duration_is_nan[-1] >= duration.shape[0] - min_consecutive_points:
                duration[duration_is_nan[-1]:] = np.nan
            # Indexes, where gap between spaces <= min_consecutive_points:
            space_nan = np.where(duration_is_nan[1:] - duration_is_nan[:-1] <= min_consecutive_points)[0]
            for index in space_nan:
                duration[duration_is_nan[index]:duration_is_nan[index + 1]] = np.nan
        df['Duration'] = duration

        # Distance
        cos_angle = (
            sin_lat * sin_lat.shift(1) + cos_lat * cos_lat.shift(1) * np.cos(longitude_rad - longitude_rad.shift(1))
        ).clip(-1, 1)   # rounding errors can create values slightly above 1
        distance = (np.arccos(cos_angle) * EARTH_RADIUS).to_numpy()
        distance[0] = 0
        distance[np.isnan(duration)] = np.nan
        df['Distance'] = distance

        # Speed
        for window in (5, 50):
            duration_rolling_sum = df['Duration'].rolling(window=window, min_periods=min_periods).sum()
            distance_rolling_sum = df['Distance'].rolling(window=window, min_periods=min_periods).sum()
            df[f'Speed_{window}'] = (distance_rolling_sum / duration_rolling_sum * 3600).replace(
                [np.inf, -np.inf], np.nan
            )

    @classmethod
    def import_gpx_file_to_database(cls):
        gpx_ignore_files = set(GPSFilesToIgnore.objects.values_list('filename', flat=True))
        known_files = set(cls.objects.values_list('filename', flat=True))
        # Get all gpxfiles that are not in the database
        gpx_files = []
        for folder in GPX_FOLDERS:
            for foldername, subfolders, filenames in os.walk(folder):
                gpx_files += [
                    (foldername, filename) for filename in filenames
                    if filename.endswith(".gpx") and
                    filename not in gpx_ignore_files and
                    filename not in known_files and
                    filename not in cls.already_tried_files and  # don't try to read files again and again
                    not filename.startswith("tour_wrong_date")  # date in BT747 gpx files needs to be offset by 1C00
                ]

        def to_int_or_none(value):
            return None if np.isnan(value) else int(round(value))

        imported = 0
        for foldername, filename in gpx_files:
            df = cls.read_gpx_file(os.path.join(foldername, filename))
            if df is None or df.shape[0] < 20:
                logger.warning(f"Ignored {0 if df is None else df.shape[0]} points from {filename}")
                cls.already_tried_files.append(filename)
                continue

            alt_adjust_text = cls.adjust_elevation(df)
            cls.calculate_track_values(df)

            # Store the data
            with transaction.atomic():
                track = cls(
                    filename=filename,
                    start_time=df['Timestamp'].iloc[0],
                    end_time=df['Timestamp'].iloc[-1],
                    number_entries=df.shape[0],
                    total_distance_m=int(round(np.nansum(df['Distance']) * 1000)),
                )
                track.save(run_backup=False)
                GPSPoint.objects.bulk_create([
                    GPSPoint(
                        track=track,
                        timestamp=row.Timestamp,
                        latitude=row.Latitude_deg,
                        longitude=row.Longitude_deg,
                        elevation=to_int_or_none(row.Elevation),
                        ele_srtm=to_int_or_none(row.Elevation_srtm),
                        speed=None if np.isnan(row.Speed_5) else float(row.Speed_5),
                    )
                    for row in df.itertuples(index=False)
                ], batch_size=1000)
            imported += 1
            logger.info(f"Loaded {df.shape[0]} points from {filename}{alt_adjust_text}")

        if imported:
            # Only dump the tables once all files are imported
            cls.backup(GPSTrack())


class GPSPoint(models.Model):
    track = models.ForeignKey(GPSTrack, on_delete=models.CASCADE, related_name='points')
    timestamp = models.DateTimeField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    elevation = models.IntegerField(null=True, blank=True)
    ele_srtm = models.IntegerField(null=True, blank=True)
    speed = models.FloatField(null=True, blank=True, help_text="Speed in km/h averaged over 5 points")

    table_name = 'GPSPoint'

    class Meta:
        ordering = ['timestamp', 'track']
        indexes = [
            models.Index(fields=['track', 'timestamp']),
        ]

    def __str__(self):
        return f"Point of {self.track} at {self.timestamp} ({self.latitude}, {self.longitude})"

    @classmethod
    def load_data(cls):
        backup_instance.load_database_dump(cls.table_name)


class GPSData(models.Model):
    filename = models.CharField(primary_key=True, max_length=100)
    start = models.DateTimeField()
    end = models.DateTimeField()
    datetimes = models.TextField()
    latitudes = models.TextField()
    longitudes = models.TextField()
    altitudes = models.TextField()
    alt_srtm = models.TextField()
    speeds = models.TextField(null=True)

    table_name = 'GPSData'

    already_tried_files = []

    class Meta:
        ordering = ['start']

    @property
    def number_entries(self) -> int:
        return self.datetimes.count(',') + 1

    def __str__(self):
        return f"{self.filename} - {self.number_entries}"

    def get_absolute_url(self):
        """Returns the url to access a detail record for this GPS file."""
        return reverse('gps_detail', args=[self.filename])

    def backup(self):
        backup_instance.backup_table(self.table_name, ''.encode(), csv_dump=False)

    def save(self, *args, run_backup=True, **kwargs):
        super().save(*args, **kwargs)
        if run_backup:
            self.backup()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.backup()

    @classmethod
    def load_data(cls):
        backup_instance.load_database_dump(cls.table_name)

        cls.import_gpx_file_to_database()

    @classmethod
    def import_gpx_file_to_database(cls):
        gpx_ignore_files = GPSFilesToIgnore.objects.values_list('filename', flat=True)
        # Get all gpxfiles that are not in the database
        for folder in GPX_FOLDERS:
            gpx_files = []
            for foldername, subfolders, filenames in os.walk(folder):
                gpx_files += [
                    (foldername, filename) for filename in filenames
                    if filename.endswith(".gpx") and
                        filename not in gpx_ignore_files and
                        filename not in cls.already_tried_files and  # don't try to read files again and again
                        not GPSData.objects.filter(filename=filename).exists() and
                        not filename.startswith("tour_wrong_date")  # date in BT747 gpx files needs to be offset by 1C00
                ]
        # Read the gpx files
        for ii, (foldername, filename) in enumerate(gpx_files):
            bad = False
            with open(os.path.join(foldername, filename), 'r') as gpx_file:
                gpx = gpxpy.parse(gpx_file)
                datetimes = []
                latitudes = []
                longitudes = []
                altitudes = []
                alt_srtm = []
                alt_diff = []
                for track in gpx.tracks:
                    if bad:
                        break
                    for segment in track.segments:
                        if bad:
                            break
                        for point in segment.points:
                            if not point.time:
                                logger.warning(f"Point without timestamp in {filename}: {point} - will ignore file")
                                bad = True
                                break
                            if abs(point.latitude) == 90:   # ignore dummy values
                                continue
                            if not datetimes:
                                start = point.time
                            datetimes.append(int(point.time.timestamp()))
                            latitudes.append(round(point.latitude, 5))
                            longitudes.append(round(point.longitude, 5))
                            altitudes.append(point.elevation)
                            if hasSrtm:
                                for i, elevation_data_source in enumerate({elevation_data_30m, elevation_data_90m}):
                                    try:
                                        elevation_srtm = elevation_data_source.get_altitude(
                                            latitude=point.latitude, longitude=point.longitude
                                        )
                                    # except KeyError:  # That exception is only internally to srtm
                                    #     logger.warning(f'No SRTM data for {point.latitude}, {point.longitude}')
                                    #     elevation_srtm = -1E6
                                    except srtm.exceptions.NoHeightMapDataException:
                                        if i == 1:
                                            logger.warning(f'Cannot read srtm data, will not read the file')
                                            bad = True
                                    except AssertionError as e:
                                        if str(e).startswith('Unexpected number of bytes found in'):
                                            logger.warning(f'Problem with (zipped) htg file: {e}')
                                            bad = True
                                            break
                                        else:
                                            raise
                                    else:   # no exceptions, don't try second elevation_data_source
                                        break
                                if bad:
                                    break
                                # SRTM data below 0 m has an underflow of the uint to values above 65000
                                # SRTM data that could not be determined because of too steep landscape is set to 32768
                                alt_srtm.append(
                                    -1 if elevation_srtm > 65000 else
                                    elevation_srtm if elevation_srtm < 30000 else -1 # np.nan
                                )
                                diff = elevation_srtm - point.elevation
                                if abs(diff) < 200:
                                    alt_diff.append(diff)

                    end = point.time
                if bad or len(datetimes) < 20:
                    logger.warning(f"Ignored {len(datetimes)} points from {filename}")
                    cls.already_tried_files.append(filename)
                else:
                    alt_adjust_text = ''
                    if len(alt_diff) > 50:
                        alt_adjust = np.median(alt_diff)
                        if abs(alt_adjust) >= 10:   # Some devices don't record the correct gps elevation
                            for i in range(len(altitudes)):
                                altitudes[i] = altitudes[i] + alt_adjust
                            alt_adjust_text = f', moved altitudes by {alt_adjust:.1f}m to match SRTM'
                    for i in range(len(altitudes)):
                        altitudes[i] = int(round(altitudes[i]))
                    obj = GPSData(
                        filename=filename, start=start, end=end, datetimes=json.dumps(datetimes),
                        latitudes=json.dumps(latitudes), longitudes=json.dumps(longitudes),
                        altitudes=json.dumps(altitudes), alt_srtm=json.dumps(alt_srtm)
                    )
                    # not just -1 but -10, as otherwise empty files can be an issue
                    # obj.save(run_backup=(ii >= len(gpx_files)-(min(10, len(gpx_files)))))
                    obj.save()
                    logger.info(f"Loaded {len(datetimes)} points from {filename}{alt_adjust_text}")
        if gpx_files:
            cls.backup(GPSData())

class NoGoAreas(models.Model):
    name = models.TextField(primary_key=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    radius = models.FloatField()
    auto_whole_world = "Auto whole world"

    table_name = 'NoGoAreas'

    def backup(self):
        data_string = ""
        for obj in NoGoAreas.objects.all():
            data_string += f"{obj.name};{obj.latitude};{obj.longitude};{obj.radius};\n"

        backup_instance.backup_table(self.table_name, data_string.encode())

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.backup()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.backup()

    @classmethod
    def load_data(cls):
        try:
            NoGoAreas.objects.filter(pk=cls.auto_whole_world).delete()
        except NoGoAreas.DoesNotExist:
            pass
        backup_instance.load_database_dump(cls.table_name)
        if NoGoAreas.objects.all().count() == 0:
            logger.warning(f"No no-go-area defined, hence will create one for the whole world")
            obj = NoGoAreas(name=cls.auto_whole_world, latitude=0., longitude=0, radius=40000.)
            obj.save()


class GeoLocateData(models.Model):
    name = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    radius = models.FloatField()

    table_name = 'GeoLocateData'

    class Meta:
        unique_together = (('name', 'latitude', 'longitude'),)

    @property
    def identifier(self):
        return f"{self.name}_{self.latitude}_{self.longitude}".replace('.', '_').replace(' ', '')

    def backup(self):
        data_string = ""
        for obj in GeoLocateData.objects.all():
            data_string += f"{obj.name};{obj.latitude};{obj.longitude};{obj.radius};\n"

        backup_instance.backup_table(self.table_name, data_string.encode())

    def save(self, *args, run_backup=True, **kwargs):
        super().save(*args, **kwargs)
        if run_backup:
            self.backup()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.backup()

    @classmethod
    def load_data(cls):
        loaded_backup = backup_instance.load_database_dump(cls.table_name)
        if GeoLocateData.objects.all().count() == 0:
            loaded_backup = backup_instance.load_backup_GeoLocateData_file_based()


class PhotoData(models.Model):
    filename = models.TextField(primary_key=True)
    description = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    thumbnail = models.BinaryField()

    table_name = 'PhotoData'

    def __str__(self):
        return self.filename

    @property
    def identifier(self):
        # A unique identifier
        return f"{self.filename}_{self.latitude}_{self.longitude}".replace('.', '_').replace(' ', '')

    @property
    def full_filename(self):
        return photoStorage.full_fillname_or_false(self.filename)

    @property
    def dimensions(self):
        # get the Thumbnail dimensions
        image = Image.open(io.BytesIO(self.thumbnail))
        return {'width': image.width, 'height': image.height}

    def backup(self):
        data_string = ""
        for obj in PhotoData.objects.all():
            data_string += f"{obj.filename};{obj.description};{obj.latitude};{obj.longitude};\n"

        backup_instance.backup_table(self.table_name, data_string.encode())

    def save(self, *args, run_backup=True, **kwargs):
        super().save(*args, **kwargs)
        if run_backup:
            self.backup()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.backup()

    @classmethod
    def load_data(cls):
        backup_instance.load_database_dump(cls.table_name)
        cls.store_files_in_static_folder()

    @classmethod
    def store_files_in_static_folder(cls):
        # Link all the used photos into the static folder
        if settings.DEBUG:
            image_folder = os.path.join(settings.STATICFILES_DIRS[0], 'images')
        else:
            image_folder = os.path.join(settings.STATIC_ROOT, 'images')
        if not settings.DEBUG and not os.path.isdir(image_folder):
            # Create folder, if necessary
            os.mkdir(image_folder)
        for obj in PhotoData.objects.all():
            static_link = os.path.join(image_folder, obj.filename)
            if not os.path.isfile(static_link) and obj.full_filename:
                # a broken link will also enter here, but will raise a FileExistsError
                try:
                    os.symlink(obj.full_filename, static_link)
                except FileExistsError:
                    os.unlink(static_link)
                    os.symlink(obj.full_filename, static_link)

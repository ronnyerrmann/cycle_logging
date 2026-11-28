import gzip
import json
import os
import random
from datetime import date, datetime, timezone
from django.core.serializers.base import DeserializationError
from django.test import TestCase
from unittest.mock import call, MagicMock, mock_open, patch

from cycle.backup import Backup

MODULE_PATH = "cycle.backup."


class BackupTest(TestCase):

    def setUp(self) -> None:
        with patch(MODULE_PATH + 'BACKUP_FOLDER', 'bd'):
            self.backup = Backup()


@patch(MODULE_PATH + "os.remove")
@patch(MODULE_PATH + "glob.glob")
@patch(MODULE_PATH + 'BACKUP_FOLDER', 'bd')
class TestRemoveFiles(BackupTest):

    def test_remove_files(self, _glob, _remove):
        file_list = ["bd/CycleRides_20230404_123456.csv.gz", "bd/CycleRides_20230404_234500.csv.gz", "bd/CycleRides_20230406_123456.csv.gz",
                     "bd/CycleRides_20230504_123456.csv.gz", "bd/CycleRides_20230504_234500.csv.gz", "bd/CycleRides_20230506_123456.csv.gz",
                     "bd/CycleRides_20230601_012345.csv.gz"] + [f"bd/CycleRides_20230602_0{ii}2345.csv.gz" for ii in range(10)]
        random.shuffle(file_list)
        _glob.return_value = file_list

        with patch(MODULE_PATH + "datetime.date") as mock_date:
            # This is required instead of a @patch
            mock_date.today.return_value = date(2023, 6, 20)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            self.backup.remove_old_files("CycleRides")

        _glob.assert_called_once_with("bd/CycleRides_*.csv.gz")
        self.assertEqual(
            sorted([
                call("bd/CycleRides_20230404_234500.csv.gz"), call("bd/CycleRides_20230406_123456.csv.gz"),
                call("bd/CycleRides_20230504_234500.csv.gz"), call("bd/CycleRides_20230506_123456.csv.gz")
            ]), sorted(_remove.call_args_list)
        )


@patch("cycle.models.CycleRides.objects.all", MagicMock(return_value=[]))     # write no data for now
@patch(MODULE_PATH + "Backup.remove_old_files")
@patch(MODULE_PATH + 'BACKUP_FOLDER', 'bd')
class TestBackupDB(BackupTest):

    def test(self, _remove_old_files):
        m = mock_open()

        with patch(MODULE_PATH + "gzip.open", m):
            with patch(MODULE_PATH + "datetime.datetime") as mock_datetime:
                # This is required instead of a @patch
                mock_datetime.now.return_value = datetime(2023, 6, 20, 12, 23, 34)
                mock_datetime.side_effect = lambda *args, **kw: date(*args, **kw)

                self.backup.backup_table('CycleRides', ''.encode())

        self.assertEqual([
            call('bd/CycleRides_20230620_122334.csv.gz', 'w'),
            call('bd/CycleRides_dump.json.gz', 'wt'),
        ], m.call_args_list)

        _remove_old_files.assert_called_once_with("bd")


@patch(MODULE_PATH + "create_folder_if_required")
class TestBackupDB(TestCase):

    def test(self, _create_folder_if_required):
        with patch(MODULE_PATH + 'BACKUP_FOLDER', 'bd'):
            self.backup = Backup()

        _create_folder_if_required.assert_called_once_with("bd")


class TestBulkLoadJsonDump(TestCase):

    def setUp(self) -> None:
        import tempfile
        from cycle.models import GPSTrack
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.filename = os.path.join(self.tmp_dir.name, "GPSPoint_dump.json.gz")
        self.objects = [
            {"model": "cycle.gpspoint", "pk": ii, "fields": {
                "track": ["track1.gpx"], "timestamp": f"2026-08-30T12:10:{ii:02d}Z", "latitude": 52.1 + ii / 1000,
                "longitude": 0.16, "elevation": 37 if ii % 2 else None, "ele_srtm": 40, "speed": None}}
            for ii in range(1, 30)
        ]
        with gzip.open(self.filename, "wt") as f:
            json.dump(self.objects, f)     # single line, like dumpdata
        for filename in ("other.gpx", "track1.gpx"):     # other.gpx, so the track id is not 1
            GPSTrack(filename=filename, start_time=datetime(2026, 8, 30, tzinfo=timezone.utc),
                     end_time=datetime(2026, 8, 30, tzinfo=timezone.utc), number_entries=29, total_distance_m=100
                     ).save(run_backup=False)
        self.track = GPSTrack.objects.get(filename="track1.gpx")

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_iter_small_chunks(self):
        # chunks smaller than an object force objects to be split over chunk boundaries
        for chunk_size in (7, 50, 1 << 20):
            self.assertEqual(self.objects, list(Backup.iter_json_dump_objects(self.filename, chunk_size=chunk_size)))

    def test_iter_empty_list(self):
        with gzip.open(self.filename, "wt") as f:
            f.write("[]")
        self.assertEqual([], list(Backup.iter_json_dump_objects(self.filename)))

    def test_load_and_update(self):
        from cycle.models import GPSPoint
        backup = Backup()
        self.assertEqual(29, backup.bulk_load_json_dump(self.filename, GPSPoint, batch_size=10))
        self.assertEqual(29, GPSPoint.objects.count())
        point = GPSPoint.objects.get(pk=3)
        self.assertEqual(self.track.pk, point.track_id)
        # old dumps have the timestamp as text, it's stored as Unix seconds
        self.assertEqual(int(datetime(2026, 8, 30, 12, 10, 3, tzinfo=timezone.utc).timestamp()), point.timestamp)
        self.assertEqual(datetime(2026, 8, 30, 12, 10, 3, tzinfo=timezone.utc), point.datetime)
        self.assertEqual(37, point.elevation)
        self.assertIsNone(GPSPoint.objects.get(pk=2).elevation)

        # Loading again updates the existing points instead of failing or duplicating them
        self.objects[2]["fields"]["elevation"] = 99
        with gzip.open(self.filename, "wt") as f:
            json.dump(self.objects, f)
        backup.bulk_load_json_dump(self.filename, GPSPoint, batch_size=10)
        self.assertEqual(29, GPSPoint.objects.count())
        self.assertEqual(99, GPSPoint.objects.get(pk=3).elevation)

    def test_load_old_format(self):
        # Dumps from before GPSTrack had an integer primary key contain the filename instead of the natural key
        from cycle.models import GPSPoint
        for obj in self.objects:
            obj["fields"]["track"] = "track1.gpx"
        with gzip.open(self.filename, "wt") as f:
            json.dump(self.objects, f)
        self.assertEqual(29, Backup().bulk_load_json_dump(self.filename, GPSPoint))
        self.assertEqual(29, GPSPoint.objects.filter(track=self.track).count())

    def test_load_timestamp_as_number(self):
        from cycle.models import GPSPoint
        for obj in self.objects:
            obj["fields"]["timestamp"] = 1788091800 + obj["pk"]
        with gzip.open(self.filename, "wt") as f:
            json.dump(self.objects, f)
        Backup().bulk_load_json_dump(self.filename, GPSPoint)
        self.assertEqual(1788091803, GPSPoint.objects.get(pk=3).timestamp)

    def test_unknown_track(self):
        from django.core.exceptions import ValidationError
        from cycle.models import GPSPoint
        self.objects[0]["fields"]["track"] = ["unknown.gpx"]
        with gzip.open(self.filename, "wt") as f:
            json.dump(self.objects, f)
        with self.assertRaises(ValidationError):
            Backup().bulk_load_json_dump(self.filename, GPSPoint)

    def test_load_tracks_by_filename(self):
        # New dumps have no pk (natural primary key), old dumps have the filename as pk: both update/insert by filename
        from cycle.models import GPSTrack
        track_objects = [
            {"model": "cycle.gpstrack", "fields": {
                "filename": "track1.gpx", "start_time": "2026-08-30T12:10:00Z", "end_time": "2026-08-30T13:10:00Z",
                "number_entries": 50, "total_distance_m": 1234}},
            {"model": "cycle.gpstrack", "pk": "new.gpx", "fields": {
                "start_time": "2026-08-31T12:10:00Z", "end_time": "2026-08-31T13:10:00Z",
                "number_entries": 60, "total_distance_m": 999}},
        ]
        with gzip.open(self.filename, "wt") as f:
            json.dump(track_objects, f)
        self.assertEqual(2, Backup().bulk_load_json_dump(self.filename, GPSTrack))
        self.assertEqual(3, GPSTrack.objects.count())
        track = GPSTrack.objects.get(filename="track1.gpx")
        self.assertEqual(self.track.pk, track.pk)    # updated, not replaced
        self.assertEqual(1234, track.total_distance_m)
        self.assertEqual(datetime(2026, 8, 30, 13, 10, tzinfo=timezone.utc), track.end_time)
        self.assertEqual(999, GPSTrack.objects.get(filename="new.gpx").total_distance_m)

    def test_wrong_model(self):
        from cycle.models import GPSPoint
        self.objects[0]["model"] = "cycle.gpstrack"
        with gzip.open(self.filename, "wt") as f:
            json.dump(self.objects, f)
        with self.assertRaises(DeserializationError):
            Backup().bulk_load_json_dump(self.filename, GPSPoint)

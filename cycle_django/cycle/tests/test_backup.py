import random
from datetime import date, datetime
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
                mock_datetime.utcnow.return_value = datetime(2023, 6, 20, 12, 23, 34)
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

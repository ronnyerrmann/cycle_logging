import random
from datetime import date, datetime
from django.test import TestCase
from unittest.mock import call, MagicMock, mock_open, patch

from cycle.backup import remove_old_files, backup_db, BACKUP_FOLDER

MODULE_PATH = "cycle.backup."


@patch(MODULE_PATH + "os.remove")
@patch(MODULE_PATH + "glob.glob")
class TestRemoveFiles(TestCase):

    def test_remove_files(self, _glob, _remove):
        file_list = ["bd/20230404_123456.csv.gz", "bd/20230404_234500.csv.gz", "bd/20230406_123456.csv.gz",
                     "bd/20230504_123456.csv.gz", "bd/20230504_234500.csv.gz", "bd/20230506_123456.csv.gz",
                     "bd/20230601_012345.csv.gz"] + [f"bd/20230602_0{ii}2345.csv.gz" for ii in range(10)]
        random.shuffle(file_list)
        _glob.return_value = file_list

        with patch(MODULE_PATH + "datetime.date") as mock_date:
            # This is required instead of a @patch
            mock_date.today.return_value = date(2023, 6, 20)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            remove_old_files("bd")

        _glob.assert_called_once_with("bd/*.csv.gz")
        self.assertEqual(
            sorted([
                call("bd/20230404_234500.csv.gz"), call("bd/20230406_123456.csv.gz"), call("bd/20230504_234500.csv.gz"),
                call("bd/20230506_123456.csv.gz")
            ]), sorted(_remove.call_args_list)
        )


@patch("cycle.models.FahrradRides.objects.all", MagicMock(return_value=[]))     # write no data for now
@patch(MODULE_PATH + "remove_old_files")
@patch(MODULE_PATH + "create_folder_if_required")
class TestBackupDB(TestCase):

    def test(self, _create_folder_if_required, _remove_old_files):
        m = mock_open()

        with patch(MODULE_PATH + "gzip.open", m):
            with patch(MODULE_PATH + "datetime.datetime") as mock_datetime:
                # This is required instead of a @patch
                mock_datetime.utcnow.return_value = datetime(2023, 6, 20, 12, 23, 34)
                mock_datetime.side_effect = lambda *args, **kw: date(*args, **kw)

                backup_db()

        self.assertEqual([
            call('backup_database/20230620_122334.csv.gz', 'w'),
            call('backup_database/FahrradRides_dump.json.gz', 'wt'),
        ], m.call_args_list)

        _create_folder_if_required.assert_called_once_with(BACKUP_FOLDER)
        _remove_old_files.assert_called_once_with(BACKUP_FOLDER)

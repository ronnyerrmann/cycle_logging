import datetime
from django.db import connection, transaction
from django.test import TestCase
from unittest.mock import MagicMock, patch

from cycle.models import convert_to_str_hours, FahrradRides


class TestConvertToStrHours(TestCase):

    def test_int_to_str(self):
        value = convert_to_str_hours(912345)

        self.assertEqual("253:25:45", value)

    def test_datetime_to_str(self):
        value = convert_to_str_hours(datetime.timedelta(days=7, seconds=3642))

        self.assertEqual("169:00:42", value)

    def test_float_to_str(self):
        value = convert_to_str_hours(912345.12)

        self.assertEqual("253:25:45", value)

    def test_None_to_str(self):
        value = convert_to_str_hours(None)

        self.assertIsNone(value)

    def test_fail(self):
        with self.assertRaises(ValueError) as test:
            convert_to_str_hours(MagicMock())

        self.assertEqual("Got MagicMock instead of int or timedelta", str(test.exception))


"""class TestFahrradRides(TestCase):

    def setUp(self) -> None:
        super().setUp()

        #FahrradRides.objects.create(date="2023-06-17", daykm=12.34, dayseconds=2345, totalkm=34.5, totalseconds=4567)

    @patch("cycle.backup.backup_db")
    def test_save(self, _backup_db):
        obj = FahrradRides.objects[0]
        obj.save()

        _backup_db.assert_called_once_with()"""
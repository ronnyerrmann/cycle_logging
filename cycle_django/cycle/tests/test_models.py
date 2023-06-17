import datetime
from django.db import connection, transaction
from django.test import TestCase
from unittest.mock import MagicMock, patch

from cycle.models import TimeInSecondsField, FahrradRides


class TestTimeInSecondsField(TestCase):

    def setUp(self) -> None:
        self.field = TimeInSecondsField()

    def test_int_to_str(self):
        value = self.field.from_db_value(912345, None, None)

        self.assertEqual("253:25:45", value)

    def test_None_to_str(self):
        value = self.field.from_db_value(None, None, None)

        self.assertIsNone(value)

    def test_float_to_str(self):
        with self.assertRaises(ValueError) as test:
            self.field.from_db_value(1.2, None, None)

        self.assertEqual("Got float instead of int", str(test.exception))

    def test_to_python_str(self):
        value = self.field.to_python("253:25:45")

        self.assertEqual(912345, value)

    def test_to_python_int(self):
        value = self.field.to_python(123)

        self.assertEqual(123, value)

    def test_to_python_None(self):
        value = self.field.to_python(None)

        self.assertIsNone(value)

    def test_to_python_timedelta(self):
        value = self.field.get_prep_value(datetime.timedelta(1, 23456))

        self.assertEqual(109856, value)

    def test_to_python_wrong(self):
        with self.assertRaises(ValueError) as test:
            self.field.to_python(1.2)

        self.assertEqual("Expected a timedelta object, got float", str(test.exception))


def change_managed_settings_just_for_tests():
    """django model managed bit needs to be switched for tests."""
    from django.apps import apps

    unmanaged_models = [m for m in apps.get_models() if not m._meta.managed]
    for m in unmanaged_models:
        m._meta.managed = True


#change_managed_settings_just_for_tests()


"""class TestFahrradRides(TestCase):

    def setUp(self) -> None:
        super().setUp()

        #FahrradRides.objects.create(date="2023-06-17", daykm=12.34, dayseconds=2345, totalkm=34.5, totalseconds=4567)

    @patch("cycle.backup.backup_db")
    def test_save(self, _backup_db):
        obj = FahrradRides.objects[0]
        obj.save()

        _backup_db.assert_called_once_with()"""
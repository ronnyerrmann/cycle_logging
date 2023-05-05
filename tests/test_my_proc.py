import unittest
from unittest.mock import patch, MagicMock

import logging

from my_proc import Logging, Mysqlset, logger


class Test_Logging(unittest.TestCase):
    def test_exists(self):
        Logging._loggers = {"foo": "bar"}

        logger = Logging.setup_logger("foo")

        self.assertEqual("bar", logger)

    @patch("my_proc.logging")
    def test(self, _logging):
        loggger_mock = MagicMock()
        _logging.getLogger.return_value = loggger_mock

        logger = Logging.setup_logger("foo")

        self.assertEqual(loggger_mock, logger)
        self.assertEqual(loggger_mock, Logging._loggers["foo"])
        _logging.Formatter.assert_called_once_with(fmt="%(asctime)s.%(msecs)03d %(name)s %(levelname)s %(message)s",
                                                   datefmt="%Y-%m-%d %H:%M:%S")
        loggger_mock.setLevel.assert_called_once_with(logging.INFO)
        loggger_mock.addHandler.assert_called_once_with(_logging.StreamHandler())
        _logging.StreamHandler().setFormatter.assert_called_once_with(_logging.Formatter())


class Mysqlset_Test(unittest.TestCase):
    def setUp(self):
        self.mysql = Mysqlset("foo", "bar", "baz", "egg")


class Test_Mysqlset_init(Mysqlset_Test):
    def test(self):
        self.assertEqual({"host": "foo", "user": "bar", "password": "baz", "database": "egg"}, self.mysql._mysqlsettings)


@patch("my_proc.mysql.connector.connect")
class Test_Mysqlset_connect(Mysqlset_Test):
    def test_pass(self, _connect):
        _MySQLConnection = MagicMock()
        _connect.return_value = _MySQLConnection

        self.mysql.connect()

        _connect.assert_called_once_with(host="foo", user="bar", password="baz", database="egg")
        self.assertEqual(_MySQLConnection, self.mysql._mydb)
        self.assertEqual(_MySQLConnection.cursor(), self.mysql._mycursor)

    def test_already_connected(self, _connect):
        self.mysql._mydb = "foo"

        with self.assertLogs(logger) as logs:
            self.mysql.connect()

        self.assertEqual(["WARNING:my_proc:Already connected, close connection first"], logs.output)
        self.assertEqual("foo", self.mysql._mydb)
        self.assertIsNone(self.mysql._mycursor)

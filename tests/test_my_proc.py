import unittest
from unittest.mock import call, MagicMock, patch

import logging

from my_proc import Logging, Mysqlset, MySQLError, logger


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
        self.mysql._mydb = MagicMock()
        self.mysql._mycursor = MagicMock()


class Test_Mysqlset_init(Mysqlset_Test):
    def test(self):
        self.assertEqual({"host": "foo", "user": "bar", "password": "baz", "database": "egg"}, self.mysql._mysqlsettings)


@patch("my_proc.mysql.connector.connect")
class Test_Mysqlset_connect(Mysqlset_Test):
    def test_pass(self, _connect):
        self.mysql._mydb = None
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


class Test_Mysqlset_execute(Mysqlset_Test):
    def test_not_connected(self):
        self.mysql._mydb = None
        self.mysql._mycursor = None

        with self.assertRaises(MySQLError) as e:
            self.mysql.execute("foo")

        self.assertEqual("Not connected to data base", str(e.exception))

    def test_clear(self):
        self.mysql._cleared = False
        mockManager = MagicMock()
        mockManager.attach_mock(self.mysql._mycursor.nextset, "nextset")
        mockManager.attach_mock(self.mysql._mycursor.execute, "execute")

        self.mysql.execute("foo")

        self.assertFalse(self.mysql._cleared)
        self.assertEqual([call.nextset(), call.execute("foo")], mockManager.mock_calls)

    def test_no_clear(self):
        self.mysql.execute("foo")

        self.assertFalse(self.mysql._cleared)
        self.mysql._mycursor.nextset.assert_not_called()
        self.mysql._mycursor.execute.assert_called_once_with("foo")


class Test_Mysqlset_get_results(Mysqlset_Test):
    def test_get_results(self):
        self.mysql._mycursor = MagicMock(fetchall=MagicMock(return_value="bar"))
        self.mysql._cleared = False
        mockManager = MagicMock()
        mockManager.attach_mock(self.mysql._mycursor.execute, "execute")
        mockManager.attach_mock(self.mysql._mycursor.fetchall, "fetchall")

        result = self.mysql.get_results("foo")

        self.assertEqual("bar", result)
        self.assertEqual([call.execute("foo"), call.fetchall()], mockManager.mock_calls)



class Test_Mysqlset_commit(Mysqlset_Test):
    def test(self):
        self.mysql.commit()

        self.mysql._mydb.commit.assert_called_once()


class Test_Mysqlset_close(Mysqlset_Test):

    def test_pass(self):
        mockManager = MagicMock()
        mockManager.attach_mock(self.mysql._mydb.close, "mydb_close")
        mockManager.attach_mock(self.mysql._mycursor.close, "mycursor_close")

        self.mysql.close()

        self.assertIsNone(self.mysql._mydb)
        self.assertIsNone(self.mysql._mycursor)
        self.assertEqual([call.mycursor_close(), call.mydb_close()], mockManager.mock_calls)

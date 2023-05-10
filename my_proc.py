#!/usr/bin/env python

__author__ = "Ronny Errmann"
__copyright__ = "Copyright 2022, Ronny"
__credits__ = ["Thanks"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Ronny Errmann"
__email__ = "ronny.errmann@gmail.com"
__status__ = "Development"

import logging
import mysql.connector
import numpy as np
import os
import sys


class Logging:
    _loggers = {}

    @classmethod
    def setup_logger(cls, name: str, level=logging.INFO):
        if name in cls._loggers.keys():
            return cls._loggers[name]

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(fmt=f"%(asctime)s.%(msecs)03d %(name)s %(levelname)s %(message)s",
                                               datefmt="%Y-%m-%d %H:%M:%S"))
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.addHandler(handler)
        cls._loggers[name] = logger
        return logger


logger = Logging.setup_logger(__name__)


def read_parameterfile(parameterfile: str):
    # load text file (remove all white spaces)
    if not os.path.exists(parameterfile):
        logger.error('The parameterfile {0} does not exist.'.format(parameterfile))
    try:
        keys, values = np.genfromtxt(
            parameterfile, dtype=str, comments='#', delimiter='=', filling_values='', autostrip=True, unpack=True
        )
    except ValueError as error:
        logger.error(f'One line (see previous output (empty lines are missing in the line number counting)) in file '
                     f'{parameterfile} has the wrong format. Expected was "parameter = value(s)". '
                     f'Please check if the "=" sign is there or if a comment "#" is missing.')

    if len(keys) == 0 or len(values) == 0:
        logger.error(f'No values found when reading the parameterfile {parameterfile}.')
    textparams = dict(zip(keys, values))
    
    return textparams


class MySQLError(Exception):
    pass

class Mysqlset():
    def __init__(self, host: str = None, user: str = None, password: str = None, database: str = None):
        self._mysqlsettings = dict(host=host, user=user, password=password, database=database)
        self._mydb = None
        self._mycursor = None
        self._cleared = True

    def read_settings_file(self, mysqlsettingsfile):
        # Read settings file
        if os.path.exists(mysqlsettingsfile):
            mysqlsettings_read = read_parameterfile(mysqlsettingsfile)
            mysqlsettings_read["database"] = mysqlsettings_read.pop("db")
            self._mysqlsettings.update(mysqlsettings_read)        # Parameters from the settingsfile have priority
            text = 'Read file: {0}, using information: {1}'
            
        else:
            text = 'No file: {0}, keeping the hardcoded information: {1}'
        logger.info(text.format(mysqlsettingsfile, self._mysqlsettings))

    def get_settings(self):
        return self._mysqlsettings

    def connect(self):
        """ Connect to database
            One would have only one connection to database per host, but can have several cursors
        """
        if self._mydb:
            logger.warning("Already connected, close connection first")
            return

        try:
            self._mydb = mysql.connector.connect(**self._mysqlsettings)
        except (mysql.connector.Error, mysql.connector.Warning) as e:
            raise

        self._mycursor = self._mydb.cursor()

    def _check_connected(self):
        if self._mydb is None or self._mycursor is None:
            raise MySQLError("Not connected to data base")


    def execute(self, cmd: str):
        self._check_connected()

        self._prepare_next_set()

        self._mycursor.execute(cmd)
        self._cleared = False


    def _prepare_next_set(self):
        if not self._cleared:
            self._mycursor.nextset()
            self._cleared = True

    def get_results(self, cmd: str):
        self.execute(cmd)
        return self._mycursor.fetchall()

    def commit(self):
        self._check_connected()
        #self.execute("COMMIT")
        self._mydb.commit()

    def close(self):
        self._check_connected()

        self._mycursor.close()
        self._mycursor = None

        self._mydb.close()
        self._mydb = None

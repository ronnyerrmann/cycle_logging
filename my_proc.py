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

#!/usr/bin/env python

__author__ = "Ronny Errmann"
__copyright__ = "Copyright 2022, Ronny"
__credits__ = ["Thanks"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Ronny Errmann"
__email__ = "ronny.errmann@gmail.com"
__status__ = "Development"

import os
import numpy as np

def read_parameterfile(parameterfile):
    # load text file (remove all white spaces)
    if not os.path.exists(parameterfile):
        print('Error: The parameterfile {0} does not exist.'.format(parameterfile))
    """ # Extra steps to check that the user didn't make mistakes in the file:
    data = read_text_file(textfile, no_empty_lines=True)
    data = convert_readfile(data, [str,str], delimiter='=', replaces=[' ', '\t',['\\',' ']], ignorelines=['#'])     # this replaces too many spaces
    for line in data:
        if len(line) != 2:
            print(('Error: The line in file {0} containing the entries {1} has the wrong format. Expected was "parameter = value(s)" .'+\
                    'Please check if the "=" sign is there or if a comment "#" is missing.').format(textfile, line))"""
    try:
        keys, values = np.genfromtxt(parameterfile, dtype=str, comments='#', delimiter='=', filling_values='', autostrip=True, unpack=True)
    except ValueError as error:
        print(error)
        print(('Error: One line (see previous output (empty lines are missing in the line number counting)) in file {0} has the wrong format. Expected was "parameter = value(s)" .'+\
            'Please check if the "=" sign is there or if a comment "#" is missing.').format(textfile))
        # raise                 # just this to show the error
        # raise ValueError      # Don't do this, you'll lose the stack trace!
    if len(keys) == 0 or len(values) == 0:
        print('Error: No values found when reading the parameterfile {0}.'.format(textfile))
    textparams = dict(zip(keys, values))
    
    return textparams


class mysqlset():
    def __init__(self, mysqlsettings_user=dict()):
        mysqlhost = "localhost"             # will be overwritten by value in mysqlsettingsfile, if exists
        mysqluser = "username"          # will be overwritten by value in mysqlsettingsfile, if exists
        mysqlpassword = "password"      # will be overwritten by value in mysqlsettingsfile, if exists
        db = "database"                      # will be overwritten by value in mysqlsettingsfile, if exists
        self.mysqlsettings = dict(host=mysqlhost, user=mysqluser, password=mysqlpassword, db=db)
        self.mysqlsettings.update(mysqlsettings_user)        # Parameters from the settingsfile have priority
    
    def read_file(self, mysqlsettingsfile):
        # Read settings file
        if os.path.exists(mysqlsettingsfile):
            mysqlsettings_read = read_parameterfile(mysqlsettingsfile)
            self.mysqlsettings.update(mysqlsettings_read)        # Parameters from the settingsfile have priority
            text = 'Read file: {0}, using information: {1}'
            
        else:
            text = 'No file: {0}, keeping the hardcoded information: {1}'
        print(text.format(mysqlsettingsfile, self.mysqlsettings))
    #return mysqlsettings

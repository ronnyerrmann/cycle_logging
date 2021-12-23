#!/usr/bin/env python

__author__ = "Ronny Errmann"
__copyright__ = "Copyright 2021, Ronny"
__credits__ = ["Thanks"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Ronny Errmann"
__email__ = "ronny.errmann@gmail.com"
__status__ = "Development"

import sys
import os
import mysql.connector
import datetime
import time
import numpy as np

# csv file parameters
number_of_header_lines = 1          # Number of lines in the header
# What column in csv file goes in what column in the database, e.g. second column in csv will be column "DayKM" in mysql
entries_for_mysql = ["Date", "DayKM", "DaySeconds", "TotalKM", "TotalSeconds"]      # Use "dummy" for columns to ignore in csv
# mysql parameters
mysqlhost = "localhost"             # will be overwritten by value in mysqlsettingsfile, if exists
mysqluser = "yourusername"          # will be overwritten by value in mysqlsettingsfile, if exists
mysqlpassword = "yourpassword"      # will be overwritten by value in mysqlsettingsfile, if exists
# Parameters host, user, password can come from mysqlsettingsfile
mysqlsettingsfile = "fahrrad_mysql.params"      # optional settings file (sensitive information is not hardcoded); Format: "parameter = value", Comments start with "#", number of spaces doesn't matter

def read_text_file(filename, no_empty_lines=False, warn_missing_file=True):
    """
    Read a textfile and put it into a list, one entry per line
    Empty lines means they consist only of tabs and spaces
    """
    text = []
    if os.path.isfile(filename):
        text1 = open(filename,'r').readlines()
        for line in text1:
            line = line.replace(os.linesep, '')
            linetemp = line.replace('\t', '')
            linetemp = linetemp.replace(',', '')
            linetemp = linetemp.replace(' ', '')
            if ( line == '' or linetemp == '') and no_empty_lines:
                continue
            text.append(line)
    elif warn_missing_file:
        print('Warn: File {0} does not exist, assuming empty file'.format(filename))    
    return text

def convert_readfile(input_list, textformats, delimiter='\t', replaces=[], ignorelines=[], expand_input=False, shorten_input=False, ignore_badlines=False, replacewithnan=False):
    """
    Can be used convert a read table into entries with the correct format. E.g integers, floats
        Ignories the lines which have less entries than entries in textformats
        replacements will be done before 
    :param input_list: 1D list or array of strings from a read file
    :param textformats: 1D list or array of formats, e.g. [str, str, int, float, float]. 
                        Individual entries can consist of a list of entries, then the conversion will be done in the order given, e.g. [str, [float, int], [float, '%Y-%m-%dT%H:%M:%S.%f'], float]
                        If a string is given this will be used to convert it into a datetime object
                        If a float, int, or str is run on a datetime object, then the datetime object will be converted into a number
    :param delimiter: string, used to split each line into the eleements
    :param replaces: 1D list or array of strings and/or lists of 2 strings, contains the strings which should be replaced by '' (if string) or by the second entry (if list)
    :param ignorelines: List of strings and/or lists. A list within ignorelines needs to consist of a string and the maximum position this string can be found.
                        If the string is found before the position, the entry of the input list is ignored
    :param expand_input: bool, if the line in the input_list contains less elements than textformats the line will be filled up with ''s
    :param shorten_input: bool, if the  line in the input_list contains more elements than textformats the line will be shortened to len(textformats)
    :param ignore_badlines: bool, if True will raise Warnings, if False will raise Errors (which will terminate code)
    :param replacewithnan: bool, if True and conversion with textformats is not possible will replace with NaN, otherwise will raise Warning/Error
    :retrun result_list: 2D list with numbers or strings, formated acording to textformats
    """
    # Make the textformats, replaces, and ignorelines consistent
    for index in range(len(textformats)):
        if type(textformats[index]) != list:
            textformats[index] = [textformats[index]]     # convert the single entries into list, e.g. make a list of lists
    for index in range(len(ignorelines)):
        error = False
        if type(ignorelines[index]) == str:     # only one entry
            ignorelines[index] = [ignorelines[index], 1E10]
        elif type(ignorelines[index]) == list:  # list with two entries: string, and position after which the string will be ignored
            if len(ignorelines[index]) != 2:
                error = True
        else:
            error = True
        if error:
            print('Error: Programming error: ignorelines which where hand over to convert_readfile are wrong. '+\
                   'It has to be a list consisting of strings and/or 2-entry lists of string and integer. Please check ignorelines: {0}'.format(ignorelines))
    for index in range(len(replaces)):
        error = False
        if type(replaces[index]) == str:     # only one entry
            replaces[index] = [replaces[index], '']
        elif type(replaces[index]) == list:  # list with two entries: search-string and replace-string
            if len(replaces[index]) != 2:
                error = True
        else:
            error = True
        if error:
            print('Error: Programming error: replaces which where hand over to convert_readfile are wrong. '+\
                   'It has to be a list consisting of strings and/or 2-entry lists of strings. Please check replaces: {0}'.format(replaces))
    # Convert the text
    error = {False:'Error:',True:'Warn:'}[ignore_badlines]
    result_list = []
    for entry in input_list:
        notuse = False
        for ignore in ignorelines:
            if entry.find(ignore[0]) <= ignore[1] and entry.find(ignore[0]) != -1:
                notuse = True
                break
        if notuse:
            continue
        for replce in replaces:
            entry = entry.replace(replce[0],replce[1])
        entry = entry.split(delimiter)
        if len(entry) < len(textformats):           # add extra fields, if not enough
            if expand_input:
                entry += [''] * ( len(textformats) - len(entry) )
            else:
                continue
        for index in range(len(textformats)):
            for textformat in textformats[index]:
                if type(textformat) == type:
                    if type(entry[index]) == datetime.datetime:
                        epoch = datetime.datetime.utcfromtimestamp(0)
                        entry[index] = (entry[index] - epoch).total_seconds()         # (obsdate - epoch) is a timedelta
                    try:
                        entry[index] = textformat(entry[index])
                    except:
                        if replacewithnan:
                            entry[index] = np.nan
                        else:
                            print(error+' Cannot convert {0} into a {1}. The problem happens in line {2} at index {3}.'.format(entry[index], textformat, entry, index))
                elif type(textformat) == str:
                    try:
                        entry[index] = datetime.datetime.strptime(entry[index], textformat)
                    except:
                        print(error+' Cannot convert {0} into a datetime object using the format {1}. The problem happens in list line {2} at index {3}.'.format(entry[index], textformat, entry, index))
                else:
                    print('Error: Programming error: textformats which where hand over to convert_readfile are wrong. It has to be a type or a string')
        if shorten_input and len(entry) > len(textformats):
            del entry[len(textformats):]
        result_list.append(entry)
    return result_list

def read_parameterfile(parameterfile):
    # load text file (remove all white spaces)
    if not os.path.exists(parameterfile):
        print('Error: The parameterfile {0} does not exist.'.format(parameterfile))
    """ # Extra steps to check that the user didn't make mistakes in the file:
    data = read_text_file(textfile, no_empty_lines=True)
    data = convert_readfile(data, [str,str], delimiter='=', replaces=[' ', '\t',['\\',' ']], ignorelines=['#'])         # this replaces too many spaces
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



if __name__ == "__main__":
    # Get Parameter:
    if len(sys.argv) == 1:
        print("Please give the csv file as parameter")
        exit(1)
    # Read settings file
    mysqlsettings = dict(host=mysqlhost, user=mysqluser, password=mysqlpassword)
    if os.path.exists(mysqlsettingsfile):
        mysqlsettings_read = read_parameterfile(mysqlsettingsfile)
        mysqlsettings.update(mysqlsettings_read)        # Parameters from the settingsfile have priority
        print('Read file: {0}, using information: {1}'.format(mysqlsettingsfile, mysqlsettings))
    else:
        print('No file: {0}, using hardcoded information: {1}'.format(mysqlsettingsfile, mysqlsettings))
    # Read csv file
    csvfile = sys.argv[1]
    if not os.path.exists(csvfile):
        print('Error: The parameterfile {0} does not exist.'.format(csvfile))
        exit(1)
    csvtext = read_text_file(csvfile, no_empty_lines=True)
    csv_data = convert_readfile(csvtext[number_of_header_lines:], [str]*len(entries_for_mysql), delimiter=',', replaces=[['\t',',']])   # A bit overkill, but reuses tested code
    # Convert times into seconds
    for ii in range(len(csv_data)):
        ii
    
    
    try:
        mydb = mysql.connector.connect( host=mysqlsettings['host'], user=mysqlsettings['user'], password=mysqlsettings['password'],  database='fahrrad' )
    except (mysql.connector.Error, mysql.connector.Warning) as e:
        print(e)
        exit(1)
    mycursor = mydb.cursor()
    #mycursor.execute("USE fahrrad")        # already in the connection
    
    mycursor.execute("SELECT Date, DayKM, DaySeconds, TotalKM, TotalSeconds FROM fahrrad_rides")
    myresult = mycursor.fetchall()
    print("Found {0} entries in table".format(len(myresult)))
    #print(myresult)
    mycursor.nextset()
    for entry in csv_data:
        mycursor.execute("INSERT INTO fahrrad_rides (Date, DayKM, DaySeconds, TotalKM, TotalSeconds) VALUES ('{0}', {1}, {2}, {3}, {4});".format(entry[0], entry[1], entry[2], entry[3], entry[4],))
        #INSERT INTO fahrrad_rides (Date, DayKM, DaySeconds, TotalKM, TotalSeconds)
        #    VALUES ('2021-12-20', 19.14, 43*60+39, 90796, 3968*3600+26);
    #print(
    
    

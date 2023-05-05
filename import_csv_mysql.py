#!/usr/bin/env python

__author__ = "Ronny Errmann"
__copyright__ = "Copyright 2022, Ronny"
__credits__ = ["Thanks"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Ronny Errmann"
__email__ = "ronny.errmann@gmail.com"
__status__ = "Development"

import argparse
import sys
import os
import mysql.connector
import datetime
import time
import numpy as np
from my_proc import Logging, Mysqlset
from typing import List, Union, Type

# csv file parameters
number_of_header_lines = 1          # Number of lines in the header
# What column in csv file goes in what column in the database, e.g. second column in csv will be column "DayKM" in mysql
entries_for_mysql = ["Date", "DayKM", "DaySeconds", "TotalKM", "TotalSeconds"]      # Use "dummy" for columns to ignore in csv
# Parameters host, user, password can come from mysqlsettingsfile
mysqlsettingsfile = "fahrrad_mysql.params"      # optional settings file (sensitive information is not hardcoded); Format: "parameter = value", Comments start with "#", number of spaces doesn't matter

logger = Logging.setup_logger(__name__)


def read_text_file(filename, no_empty_lines=False, warn_missing_file=True):
    """
    Read a textfile and put it into a list, one entry per line
    Empty lines means they consist only of tabs and spaces
    """
    text = []
    if os.path.isfile(filename):
        with open(filename, 'r') as file:
            for line in file.readlines():
                line = line.replace(os.linesep, '')
                if no_empty_lines:
                    if line == "":
                        continue
                    linetemp = line.replace('\t', '')
                    linetemp = linetemp.replace(',', '')
                    linetemp = linetemp.replace(' ', '')
                    if linetemp == "":
                        continue
                text.append(line)
    elif warn_missing_file:
        logger.warning(f"File {filename} does not exist, assuming empty file")
    return text

def convert_readfile(
        input_list: List[str], textformats: List[Union[List[Type], Type]], delimiter: str = '\t',
        replaces: List[Union[List, str]] = [], ignorelines: List[Union[List, str]] = [],
        expand_input: bool = False, shorten_input: bool = False, ignore_badlines: bool = False,
        replacewithnan: bool = False
):
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

    # convert the single entries into list, e.g. make a list of lists
    textformats = [entry if type(entry) == list else [entry] for entry in textformats]
    replaces = [entry if type(entry) == list else [entry, ""] for entry in replaces]
    ignorelines = [entry if type(entry) == list else [entry, 1E10] for entry in ignorelines]

    error_replaces = [entry for entry in replaces if type(entry[0]) != str or len(entry) > 2]
    if error_replaces:
        logger.error(f"Programming error: replaces which where hand over to convert_readfile are wrong. "
              f"It has to be a list consisting of strings and/or 2-entry lists of strings. "
              f"Please check replaces: {error_replaces}")
    error_ignore = [entry for entry in ignorelines if type(entry[0]) != str or len(entry) > 2]
    if error_ignore:
        logger.error(f"Programming error: ignorelines which where hand over to convert_readfile are wrong. "
              f"It has to be a list consisting of strings and/or 2-entry lists of string and integer. "
              f"Please check ignorelines: {error_ignore}")

    # Convert the text
    log_type = logger.warning if ignore_badlines else logger.error
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
            entry = entry.replace(replce[0], replce[1])
        entry = entry.split(delimiter)
        if len(entry) < len(textformats):           # add extra fields, if not enough
            if expand_input:
                entry += [''] * (len(textformats) - len(entry))
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
                            log_type(f"Cannot convert {entry[index]} into a {textformat}. The problem happens in line "
                                     f"{entry} at index {index}.")
                elif type(textformat) == str:
                    try:
                        entry[index] = datetime.datetime.strptime(entry[index], textformat)
                    except:
                        log_type(f"Cannot convert {entry[index]} into a datetime object using the format {textformat}. "
                                 f"The problem happens in list line {entry} at index {index}.")
                else:
                    logger.error("Programming error: textformats which where hand over to convert_readfile are wrong. "
                                 "It has to be a type or a string")
        if shorten_input and len(entry) > len(textformats):
            del entry[len(textformats):]
        result_list.append(entry)
    return result_list


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import values from a csv file")
    parser.add_argument(metavar="csv-file", dest="csvfile", help="The csv file with the entrie to import.")
    args = parser.parse_args()

    # Read csv file
    csvtext = read_text_file(args.csvfile, no_empty_lines=True)
    delimiters = ['\t', ',']
    for delimiter in delimiters:
        if len(csvtext[0].split(delimiter)) == len(entries_for_mysql):
            break
    else:
        raise ValueError(f"Error: Could not find the correct delimiter. Tested: {delimiters}")

    replace = []
    if delimiter == '\t':
        replace = [',']     # remove , in 43,242
    csv_data = convert_readfile(
        csvtext[number_of_header_lines:], [str]*len(entries_for_mysql), delimiter=delimiter, replaces=replace
    )   # A bit overkill, but reuses tested code
    
    # Convert times into seconds, convert dates into mysql date format, and prepare INSERT statement:
    insertlist = []
    insertindex = []
    convert_s_index, convert_d_index = [], []
    time_split = ':'
    date_convertions = ['%Y-%m-%d', '%d %b %Y', '%d. %b %Y', '%d %b. %Y', '%d. %b. %Y', '%d %B %Y', '%d. %B %Y',
                        '%d %b %y', '%d. %b %y', '%d %b. %y', '%d. %b. %y', '%d %B %y', '%d. %B %y']
    for ii in range(len(entries_for_mysql)):
        if entries_for_mysql[ii].lower() != 'dummy':
            if entries_for_mysql[ii].lower().find('second') != -1:
                convert_s_index.append(ii)
            if entries_for_mysql[ii].lower().find('date') != -1:
                convert_d_index.append(ii)
            insertlist.append(entries_for_mysql[ii])
            insertindex.append(ii)
    for ii in range(len(csv_data)):
        for jj in convert_s_index:
            result = csv_data[ii][jj]
            mult = 1
            numbers = csv_data[ii][jj].split(time_split)
            if csv_data[ii][jj][0] == "-" and numbers[0] == 0:     # Will lose minus sign
                mult = -1
            if len(numbers) == 1:       # assuming hours
                result = mult * int(numbers[0])*3600
            elif len(numbers) == 2:       # hh:mm
                result = mult * int(numbers[0])*3600 + int(numbers[1])*60
            elif len(numbers) == 3:       # hh:mm:ss
                result = mult * int(numbers[0])*3600 + int(numbers[1])*60 + int(numbers[2])
            else:
                print(f"Can't convert {csv_data[ii][jj]} into seconds, expected 0, 1, or 2 {time_split}")
            csv_data[ii][jj] = result
        for jj in convert_d_index:
            result = csv_data[ii][jj]
            for convertion in date_convertions:
                try:
                    result = datetime.datetime.strptime(csv_data[ii][jj], convertion).strftime('%Y-%m-%d')
                    break
                except ValueError as error:
                    #print(error)
                    pass
            else:
                logger.error(f"Can't convert {csv_data[ii][jj]} into date, when using the following formats: "
                             f"{date_convertions}")
            csv_data[ii][jj] = result
    
    insertstatement = f"INSERT INTO fahrrad_rides ({', '.join(insertlist)})"

    mysqlset = Mysqlset()
    mysqlset.read_settings_file(mysqlsettingsfile)
    mysqlset.connect()
    myresult = mysqlset.get_results("SELECT Date, DayKM, DaySeconds, TotalKM, TotalSeconds FROM fahrrad_rides")
    numbers = [len(myresult), 0, 0, 0]
    logger.info(f"Found {numbers[0]} entries in table")
    #print(myresult[-1]) # (datetime.date(2022, 3, 6), 55.1, 8147, 92833.0, 14579280)
    #print(csv_data[-1]) # 2022-03-06 <class 'str'>, 55.10 <class 'str'>, 8147 <class 'int'>, 92833 <class 'str'>, 14579280 <class 'int'>
    dates_in_db = np.array(['YYYY-MM-DD']*numbers[0])
    for ii in range(numbers[0]):
        dates_in_db[ii] = myresult[ii][0].strftime('%Y-%m-%d')
    for entry in csv_data:
        # before inserting, check if already there; as also a failed entry will increase an AUTO_INCREMENT PRIMARY KEY
        where_date_in_db = np.where(entry[insertindex[0]] == dates_in_db)[0]
        already_in_db = False
        for jj in where_date_in_db:     # check for all entries in the database that have the same date
            matching_fields = []
            for kk, ii in enumerate(insertindex[1:]):    # check for all fields, assuming that mycursor.execute selects the same values in the right order
                if type(entry[ii]).__name__ == 'str':
                    matching_fields.append(myresult[jj][kk+1] == float(entry[ii]))
                else:
                    matching_fields.append(myresult[jj][kk+1] == entry[ii])
            already_in_db = np.all(matching_fields)
            if already_in_db:
                break
        if already_in_db:   # Don't insert, if already in the database
            numbers[3] += 1
            continue
        # Prepare the insert statement
        this_insert = insertstatement +' VALUES ('
        for ii in insertindex:
            if ii in convert_d_index:
                this_insert += "'{0}', ".format(entry[ii])  # Date needs a string conversion
            else:
                this_insert += "{0}, ".format(entry[ii])
        this_insert = this_insert[:-2] + ");"
        # Add the values into the database
        try:
            mysqlset.execute(this_insert)
            numbers[1] += 1
        except (mysql.connector.Error, mysql.connector.Warning) as e:
            logger.warning(f"Problem with statement: {this_insert}\nError message: {e}")
            numbers[2] += 1
        #INSERT INTO fahrrad_rides (Date, DayKM, DaySeconds, TotalKM, TotalSeconds)
        #    VALUES ('2021-12-20', 19.14, 43*60+39, 90796, 3968*3600+26);
    myresult = mysqlset.get_results("SELECT Date, DayKM, DaySeconds, TotalKM, TotalSeconds FROM fahrrad_rides")
    logger.info(f"Entries in database table before: {numbers[0]}, entries added: {numbers[1]}, entries failed: "
                f"{numbers[2]}, csv-entries already in database: {numbers[3]}, entries in table now: {len(myresult)}")

    mysqlset.commit()
    logger.info("Commited - Successfully finished")

    mysqlset.close()

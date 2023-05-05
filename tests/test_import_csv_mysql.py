import unittest

from import_csv_mysql import convert_readfile, logger

__import__('sys').modules['unittest.util']._MAX_LENGTH = 1000


class Test_convert_readfile(unittest.TestCase):
    def test_pass(self):
        text = ["line1-col1\tline1-col2\t1\t2", "line2-col1\tline2-col2 dont ignore\t3\t3.5", "ignore"]
        textformats = [str, str, int, float]
        replaces = ["line", ["col", "column"]]
        ignorelines = [["ignore", 5]]

        result = convert_readfile(text, textformats, delimiter='\t', replaces=replaces, ignorelines=ignorelines)

        self.assertEqual([["1-column1", "1-column2", 1, 2.0], ["2-column1", "2-column2 dont ignore", 3, 3.5]], result)

    def test_no_number(self):
        text = ["line1-col1\tline1-col2"]
        textformats = [str, int]

        with self.assertLogs(logger) as logs:
            result = convert_readfile(text, textformats, delimiter='\t')

        self.assertEqual([["line1-col1", "line1-col2"]], result)
        self.assertEqual(["ERROR:import_csv_mysql:Cannot convert line1-col2 into a <class 'int'>. The problem happens "
                          "in line ['line1-col1', 'line1-col2'] at index 1."], logs.output)

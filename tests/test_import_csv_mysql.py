import unittest

import import_csv_mysql


class Test_convert_readfile(unittest.TestCase):
    def test_pass(self):
        text = ["line1-col1\tline1-col2", "line2-col1\tline2-col2 dont ignore", "ignore"]
        textformats = [str, str]
        replaces = ["line", ["col", "column"]]
        ignorelines = [["ignore", 5]]

        result = import_csv_mysql.convert_readfile(
            text, textformats, delimiter='\t', replaces=replaces, ignorelines=ignorelines
        )

        self.assertEqual([["1-column1", "1-column2"], ["2-column1", "2-column2 dont ignore"]], result)

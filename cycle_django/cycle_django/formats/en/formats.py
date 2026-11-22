# Overrides Django's locale formats for English (see FORMAT_MODULE_PATH in settings.py)
DATE_FORMAT = "Y-m-d"
TIME_FORMAT = "H:i:s"
DATETIME_FORMAT = "Y-m-d H:i:s"
SHORT_DATE_FORMAT = "Y-m-d"
SHORT_DATETIME_FORMAT = "Y-m-d H:i"
# Accept the same formats in forms (admin input fields)
DATE_INPUT_FORMATS = ["%Y-%m-%d"]
TIME_INPUT_FORMATS = ["%H:%M:%S", "%H:%M"]
DATETIME_INPUT_FORMATS = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]

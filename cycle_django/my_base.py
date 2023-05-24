import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent      # */cycle_logging/cycle_django
MYSQL_SETTINGS_DIR = str(Path(__file__).resolve().parent.parent)    # */cycle_logging
sys.path.append(MYSQL_SETTINGS_DIR)

from my_proc import Logging, Mysqlset       # to be used by subroutines

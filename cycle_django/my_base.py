import os
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent      # */cycle_logging/cycle_django
MYSQL_SETTINGS_DIR = str(Path(__file__).resolve().parent.parent)    # */cycle_logging
sys.path.append(MYSQL_SETTINGS_DIR)

from my_proc import Logging, Mysqlset       # to be used by subroutines

logger = Logging.setup_logger(__name__)


def create_folder_if_required(folder_path):
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
    except OSError as e:
        logger.error(f"Error occurred while creating folder: {e}")
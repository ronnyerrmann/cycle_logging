import os
import sys
from pathlib import Path

production_settings_folder = "/cycle_setup"
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent      # */cycle_logging/cycle_django
parent_dir = str(Path(__file__).resolve().parent.parent)    # */cycle_logging
sys.path.append(parent_dir)
DEBUG = os.environ.get("IS_PRODUCTION", "False").lower() != "true"

from my_proc import Logging

logger = Logging.setup_logger(__name__)


if not DEBUG and os.path.exists(production_settings_folder):
    SETTINGS_DIR = production_settings_folder
else:
    SETTINGS_DIR = parent_dir

logger.info(f"DEBUG={DEBUG} and SETTINGS_DIR={SETTINGS_DIR}")

def create_folder_if_required(folder_path):
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
    except OSError as e:
        logger.error(f"Error occurred while creating folder: {e}")
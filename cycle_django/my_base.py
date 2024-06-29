import datetime
import io
import os
import pytz
import sys
from pathlib import Path
from PIL import Image
from typing import Union

production_settings_folder = "/cycle_setup"
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent      # */cycle_logging/cycle_django
parent_dir = str(Path(__file__).resolve().parent.parent)    # */cycle_logging
sys.path.append(parent_dir)
DEBUG = os.environ.get("IS_PRODUCTION", "False").lower() != "true"

GPX_FOLDERS = {"/home/ronny/Documents/gps-logger/", }
PHOTO_FOLDERS = {"/home/ronny/Pictures/", "/Pictures"}      # local laptop; docker container

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


def create_timezone_object(input_date: datetime.date) -> datetime.datetime:
    # Creates datetime object with a timezone
    timezone = pytz.timezone('UTC')
    date = datetime.datetime(input_date.year, input_date.month, input_date.day)  # , tzinfo=datetime.tzinfo('UTC'))
    return timezone.localize(date)


class PhotoStorage:
    filenames_ = set()
    def __init__(self):
        for folder in PHOTO_FOLDERS:
            for foldername, subfolders, filenames in os.walk(folder):
                self.filenames_ |= {os.path.join(foldername, filename) for filename in filenames}

    def full_fillname_or_false(self, filename: str) -> Union[bool, str]:
        for entry in self.filenames_:
            if entry.endswith(filename):
                return entry
        return False

    def create_thumbnail(self, filename: str) -> bytes:
        """ Returns the byte stream of a thumbnail, empty if filename doesn't exist"""
        full_filename = self.full_fillname_or_false(filename)
        if full_filename:
            with Image.open(full_filename) as img:
                width, height = img.size
                scale = max(width, height) / 100.
                img.thumbnail((int(width / scale), int(height / scale)))
                thumbnail_stream = io.BytesIO()
                img.save(thumbnail_stream, format='JPEG')
                thumbnail_binary = thumbnail_stream.getvalue()
                return thumbnail_binary
        return b''


photoStorage = PhotoStorage()

import os
import psutil
import threading
from django.db.utils import OperationalError

from my_base import Logging

logger = Logging.setup_logger(__name__)


class BackgroundThread(threading.Thread):
    _instance = None

    def __init__(self, interval=60):
        super().__init__()
        self.interval = interval
        self.first_interval = None
        self.stopped = threading.Event()
        self.do_first_startup_tasks()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BackgroundThread, cls).__new__(cls)
        return cls._instance

    def run(self):
        while not self.stopped.wait(self.first_interval or self.interval):
            self.load_data_if_new()
            self.first_interval = None

    def stop(self):
        self.stopped.set()

    def start(self, first_interval=None):
        pid = None
        try:
            with open('/tmp/cycle_background_task', 'r') as f:
                pid = int(f.readline().strip())
        except (OSError, ValueError) as e:
            pass
        if pid and psutil.pid_exists(pid):
            # A background process is already running
            logger.info(f"Process has already a background process: {pid}")
            return
        with open('/tmp/cycle_background_task', 'w') as f:
            f.write(str(os.getpid()))
        self.first_interval = first_interval
        super().start()

    @staticmethod
    def load_data_if_new():
        from .models import (
            Bicycles, CycleRides, CycleWeeklySummary, CycleMonthlySummary, CycleYearlySummary, NoGoAreas,
            GPSFilesToIgnore, GPSData, GeoLocateData, PhotoData
        )
        for model in Bicycles, CycleRides, NoGoAreas, GPSFilesToIgnore, GPSData, GeoLocateData, PhotoData:
            try:
                model.load_data()
            except EOFError as e:
                logger.warning(f"File was not fully transferred?: {e}")
            except OperationalError as e:
                if str(e).startswith("no such table: "):
                    logger.warning(f"Missing Table for {model}")
                elif str(e).startswith("database is locked"):
                    logger.warning(f"Database was locked when trying to load data for {model}")
                else:
                    raise
        for summary in [CycleWeeklySummary, CycleMonthlySummary, CycleYearlySummary]:
            summary.update_fields()

    def do_first_startup_tasks(self):
        from .models import PhotoData
        PhotoData.store_files_in_static_folder()
        logger.info("Finished first startup tasks")


import os
import psutil
import threading

from my_base import Logging

logger = Logging.setup_logger(__name__)


class BackgroundThread(threading.Thread):
    _instance = None

    def __init__(self, interval=60):
        super().__init__()
        self.interval = interval
        self.stopped = threading.Event()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BackgroundThread, cls).__new__(cls)
        return cls._instance

    def run(self):
        while not self.stopped.wait(self.interval):
            # Your background task logic goes here
            logger.info(f"Background task is running... {threading.get_ident()}, {threading.current_thread().ident}, {os.getpid()}")
            self.load_data()

    def stop(self):
        self.stopped.set()

    def start(self):
        pid = None
        try:
            with open('/tmp/cycle_background_task', 'r') as f:
                pid = int(f.readline().strip())
        except OSError as e:
            pass
        if pid and psutil.pid_exists(pid):
            # A background process is already running
            logger.info(f"Process has already a background process: {pid}")
            return
        with open('/tmp/cycle_background_task', 'w') as f:
            f.write(str(os.getpid()))
        super().start()

    @staticmethod
    def load_data():
        from .models import CycleRides, CycleWeeklySummary, CycleMonthlySummary, CycleYearlySummary, NoGoAreas, GPSData
        for model in CycleRides, NoGoAreas, GPSData:
            try:
                model.load_data()
            except OperationalError as e:
                if str(e).startswith("no such table: "):
                    logger.warning(f"Missing Table for {model}")
                else:
                    raise
        for summary in [CycleWeeklySummary, CycleMonthlySummary, CycleYearlySummary]:
            summary.update_fields()

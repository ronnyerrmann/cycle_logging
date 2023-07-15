import datetime
import glob
import gzip
import os
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.serializers.base import DeserializationError
from django.db.utils import OperationalError

import cycle.models
from my_base import Logging, create_folder_if_required

BACKUP_FOLDER = "backup_database"

logger = Logging.setup_logger(__name__)


class Backup:
    file_changed_last_loaded = None
    warn_db_dump_not_found = ["No database dump found"]
    warn_db_dump_old = True

    @staticmethod
    def remove_old_files(folder_path):
        files = glob.glob(os.path.join(folder_path, "*.csv.gz"))
        files.sort()

        keep_files = set()
        dates_covered = set()
        today = datetime.datetime.now()
        beginning_of_last_month = (today - datetime.timedelta(days=31)).replace(day=1, hour=0, minute=0, second=0)
        one_week_ago = today - datetime.timedelta(days=7)

        # Keep the last 10 files
        keep_files.update(files[-10:])

        for file in files:
            file_name = os.path.basename(file)
            file_date = datetime.datetime.strptime(file_name[:15], "%Y%m%d_%H%M%S")

            # For files older than 1 month, keep the first file of the month
            if file_date < beginning_of_last_month:
                month_start = file_date.replace(day=1, hour=0, minute=0, second=0)
                if month_start not in dates_covered:
                    dates_covered.add(month_start)
                    # logger.info(f"Kept file {file} because of month")
                    keep_files.add(file)

            # For files older than 1 week, keep the first file of a day
            elif file_date < one_week_ago:
                day_start = file_date.replace(hour=0, minute=0, second=0)
                if day_start not in dates_covered:
                    dates_covered.add(day_start)
                    # logger.info(f"Kept file {file} because of week")
                    keep_files.add(file)

            else:
                # logger.info(f"Kept file {file} because of young")
                keep_files.add(file)

        files_to_remove = set(files) - keep_files
        if files_to_remove:
            logger.info(f"Clean the old files: {files_to_remove}")
            for file_to_remove in files_to_remove:
                os.remove(file_to_remove)

    def backup_db(self):
        create_folder_if_required(BACKUP_FOLDER)
        self.remove_old_files(BACKUP_FOLDER)

        with gzip.open(os.path.join(BACKUP_FOLDER, datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S.csv.gz')), "w") as f:
            for obj in cycle.models.CycleRides.objects.all():
                f.write(f"{obj.date.strftime('%Y-%m-%d')};{obj.distance};{cycle.models.convert_to_str_hours(obj.duration)};"
                        f"{obj.totaldistance};{cycle.models.convert_to_str_hours(obj.totalduration)}\n".encode())

        # To load last changes on production instance
        call_command("dumpdata", "cycle.CycleRides", output=os.path.join(BACKUP_FOLDER, "CycleRides_dump.json.gz"))


    def load_backup(self):
        # "load_db_dump_at_startup" is mountpoint in Docker
        filename = os.path.join("load_db_dump_at_startup", "CycleRides_dump.json.gz")
        logger.info(f"Load db file {filename}")
        if not os.path.isfile(filename):
            if self.warn_db_dump_not_found:
                logger.warning(self.warn_db_dump_not_found.pop())
            return
        logger.info(f"Found")
        file_changed = os.path.getmtime(filename)
        if self.file_changed_last_loaded and file_changed <= self.file_changed_last_loaded:
            if self.warn_db_dump_old:
                logger.info(f"Don't load data, because it's not new {type(file_changed)}")
                self.warn_db_dump_old = False
            return
        logger.info(f"not too old {file_changed}, {self.file_changed_last_loaded}")
        try:
            call_command("loaddata", filename)
        except DeserializationError as e:
            if str(e).find("Invalid model identifier") != -1:
                logger.error(f"Deserialiser Error: {e}")
                return
            else:
                raise
        except (CommandError, OperationalError) as e:
            logger.warning(f"Couldn't load backup: {e}")
            return

        self.__class__.file_changed_last_loaded = file_changed
        logger.info(f"Load was fine {self.file_changed_last_loaded}")
        self.warn_db_dump_old = True
        return True


    def load_backup_mysql_based(self):
        """ Import the backup from the MySQL based version into this version
        - only required once
        - takes a long time for 3k entries as it only does about 5 entries per second (faster after disabling the backup)
        """
        def str_to_timedelta(text):
            data = [int(ii) for ii in (":0:0:" + text).rsplit(":", 3)[-3:]]
            return datetime.timedelta(hours=data[-3], minutes=data[-2], seconds=data[-1])

        filename = os.path.join(BACKUP_FOLDER, "20230709_202017.csv.gz")
        if os.path.isfile(filename):
            number_of_imports = 0
            with gzip.open(filename, "r") as f:
                for line in f.readlines():
                    line = line.decode().split(";")      # 2008-06-12;14.94;00:38:40;247.0;11:21:00
                    date = datetime.datetime.strptime(line[0], "%Y-%m-%d").date()
                    distance = float(line[1])
                    duration = str_to_timedelta(line[2])
                    totaldistance = float(line[3])
                    totalduration = str_to_timedelta(line[4])
                    try:
                        obj = cycle.models.CycleRides.objects.get(date=date, distance=distance, duration=duration)
                    except cycle.models.CycleRides.DoesNotExist:
                        obj = cycle.models.CycleRides(
                            date=date, distance=distance, duration=duration,
                            totaldistance=totaldistance, totalduration=totalduration
                        )
                        obj.save(no_backup=True, no_summary=True)
                        number_of_imports += 1
            if number_of_imports:
                logger.info(f"Imported {number_of_imports} entries from {filename}")
                return True

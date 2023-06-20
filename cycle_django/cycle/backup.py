import datetime
import glob
import gzip
import os
import cycle.models
from my_base import Logging, create_folder_if_required

BACKUP_FOLDER = "backup_database"

logger = Logging.setup_logger(__name__)


"""
from django.db.models.signals import post_save
from django.dispatch import receiver
@receiver(post_save, sender=FahrradRides)
def handle_object_save(sender, instance, created, **kwargs):
    # Test method on how to use receiver to react to signals
    # requires in apps.py class CycleConfig(AppConfig):
    #    def ready(self):
    #        from . import backup  # backup is this module
    #
    print(113, sender, instance, created, kwargs)
    if created:
        # Access all objects of the table
        all_objects = FahrradRides.objects.all()
        # Perform desired operations with all_objects
        for obj in all_objects:
            print(111, obj)"""


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
                keep_files.add(file)

        # For files older than 1 week, keep the first file of a day
        elif file_date < one_week_ago:
            day_start = file_date.replace(hour=0, minute=0, second=0)
            if day_start not in dates_covered:
                dates_covered.add(day_start)
                keep_files.add(file)

        else:
            keep_files.add(file)

    files_to_remove = set(files) - keep_files
    logger.info(f"Clean the old files: {files_to_remove}")
    for file_to_remove in files_to_remove:
        os.remove(file_to_remove)

def backup_db():
    create_folder_if_required(BACKUP_FOLDER)
    remove_old_files(BACKUP_FOLDER)

    with gzip.open(os.path.join(BACKUP_FOLDER, datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S.csv.gz')), "w") as f:
        for obj in cycle.models.FahrradRides.objects.all():
            f.write(f"{obj.date.strftime('%Y-%m-%d')};{obj.daykm};{obj.dayseconds};{obj.totalkm};{obj.totalseconds}"
                    f"\n".encode())



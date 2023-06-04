import gzip
import datetime
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


def backup_db():
    create_folder_if_required(BACKUP_FOLDER)

    with gzip.open(f"{BACKUP_FOLDER}/{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv.gz", "w") as f:
        for obj in cycle.models.FahrradRides.objects.all():
            f.write(f"{obj.date.strftime('%Y-%m-%d')};{obj.daykm};{obj.dayseconds};{obj.totalkm};{obj.totalseconds}"
                    f"\n".encode())


from django.db.models.signals import post_save
from django.dispatch import receiver
from cycle.models import FahrradRides, convert_sec_to_str       # this is correct


logger = Logging.setup_logger(__name__)


"""
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
    with open("backup_database.csv", "w") as f:
        for obj in FahrradRides.objects.all():
            f.write(f"{obj.date.strftime('%Y-%m-%d')};{obj.daykm};{obj.dayseconds};{obj.totalkm};{obj.totalseconds}\n")


import sys
from django.apps import AppConfig
from django.db.utils import OperationalError

from my_base import Logging, SETTINGS_DIR

logger = Logging.setup_logger(__name__)


class CycleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cycle'

    def ready(self):
        #super().ready()
        if 'makemigrations' not in sys.argv and 'migrate' not in sys.argv and 'collectstatic' not in sys.argv:
            self.add_superuser()
            self.load_data()
        logger.info("Initialisation done")

    @staticmethod
    def add_superuser():
        from django.contrib.auth.models import User

        username = 'ronny.errmann@gmail.com'
        try:
            if not User.objects.filter(username=username).exists():
                with open(SETTINGS_DIR + "/django_admin_password.txt") as f:
                    password = f.read().strip()
                superuser = User.objects.create_superuser(
                    username=username,
                    email=username,
                    password=password)
                superuser.save()
                logger.info(f"Added user {username}")
        except OperationalError as e:
            if str(e).startswith("no such table: auth_user"):
                logger.warning("Couldn't check for user")
            else:
                raise

    @staticmethod
    def load_data():
        from .models import CycleRides
        try:
            CycleRides.load_data()
        except OperationalError as e:
            if str(e).startswith("no such table: "):
                logger.warning("Missing Table for CycleRides")
            else:
                raise

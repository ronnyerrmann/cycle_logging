from django.apps import AppConfig
from django.db.utils import OperationalError

from my_base import Logging, MYSQL_SETTINGS_DIR

logger = Logging.setup_logger(__name__)


class CycleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cycle'

    def ready(self):
        #super().ready()
        self.add_superuser()
        self.load_data()
        logger.info("Initialisation done")

        """import os
        os.environ["DJANGO_SUPERUSER_PASSWORD"] = "abc"
        call_command('createsuperuser',
                     username='ronny.errmann@gmail.com',
                     email='ronny.errmann@gmail.com',
                     interactive=False,
                     )
        # Initialise the basic users once the migration finished
        import cycle.signals"""

    @staticmethod
    def add_superuser():
        from django.contrib.auth.models import User

        username = 'ronny.errmann@gmail.com'
        try:
            if not User.objects.filter(username=username).exists():
                with open(MYSQL_SETTINGS_DIR + "/django_admin_password.txt") as f:
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
        from .models import FahrradRides
        try:
            FahrradRides.load_data()
        except OperationalError as e:
            if str(e).startswith("no such table: "):
                logger.warning("Missing Table for FahrradRides")
            else:
                raise

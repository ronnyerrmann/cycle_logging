import atexit
import sys
from django.apps import AppConfig
from django.db.utils import OperationalError
from .background import BackgroundThread

from my_base import Logging, SETTINGS_DIR

logger = Logging.setup_logger(__name__)


class CycleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cycle'

    def ready(self):
        #super().ready()
        if 'makemigrations' not in sys.argv and 'migrate' not in sys.argv and 'collectstatic' not in sys.argv:
            self.add_superuser()
            self.add_bicycle_if_none()
            # more tasks are done in background.do_first_startup_tasks
            background_thread = BackgroundThread()
            background_thread.start(first_interval=1)
            atexit.register(background_thread.stop)
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
    def add_bicycle_if_none():
        from .models import Bicycles
        Bicycles.add_bicycle_if_none()

    """ # Load data from a file
        from .models import CycleRides
        def str_to_timedelta(text):
            data = [int(ii) for ii in (":0:0:" + text).rsplit(":", 3)[-3:]]
            return datetime.timedelta(hours=data[-3], minutes=data[-2], seconds=data[-1])
        import datetime
        selected = Bicycles.objects.filter(is_default=True)[0]
        with open('/tmp/cycle_tmp.txt') as f:
            for line in f.readlines():
                line = line.split()
                if len(line) < 5:
                    continue
                date = datetime.datetime.strptime(line[0], "%Y-%m-%d").date()
                distance = float(line[1])
                duration = str_to_timedelta(line[2])
                totaldistance = float(line[3])
                totalduration = str_to_timedelta(line[4]+'00')
                CycleRides(
                            date=date, distance=distance, duration=duration,
                            totaldistance=totaldistance, totalduration=totalduration, bicycle=selected
                        ).save()
        os.system('mv /tmp/cycle_tmp.txt /tmp/cycle_tmp.old')
    """

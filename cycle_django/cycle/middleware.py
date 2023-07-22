from .backup import Backup
from .models import CycleRides
from my_base import Logging

logger = Logging.setup_logger(__name__)


class PreDatabaseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed before any data is loaded from the database
        #logger.info(f"Executing code before database queries {request}")
        if Backup().load_backup():
            CycleRides.mark_summary_tables(None, update_all=True)

        # Continue with normal behaviour
        response = self.get_response(request)

        return response

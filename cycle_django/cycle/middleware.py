# from .backup import Backup
# from .models import CycleRides
# from my_base import Logging

# logger = Logging.setup_logger(__name__)


# Moved to BackgroundThread
"""class PreDatabaseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    # Moved to BackgroundThread
    def __call__(self, request):
        # Code to be executed before any data is loaded from the database
        #logger.info(f"Executing code before database queries {request}")
        if 'makemigrations' not in request.META.get('argv', []) and 'migrate' not in request.META.get('argv', []):
            if Backup().load_database_dump("CycleRides_dump.json.gz"):
                CycleRides.mark_summary_tables(None, update_all=True)

        # Continue with normal behaviour
        response = self.get_response(request)

        return response"""

import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app
# TODO (Later): Import celery when ready
# from app.extensions import celery

# TODO (Later): Uncomment when running Celery worker as standalone process
# app = create_app(os.getenv('FLASK_ENV', 'development'))
# app.app_context().push()

# TODO (Later): Define Celery task by uncommenting decorator
# @celery.task
def run_silent_analysis(statement_id, case_id):
    """
    Background job to run all detectors silently.
    M2, M3, M4 will add their detectors here.
    """
    print(f"Starting silent analysis for statement_id: {statement_id}, case_id: {case_id}")
    
    # M1 creates the skeleton, others fill it
    # TODO: Fetch statement & transactions
    # TODO: Run detectors
    # TODO: Save detection results
    
    print(f"Completed silent analysis for statement_id: {statement_id}")

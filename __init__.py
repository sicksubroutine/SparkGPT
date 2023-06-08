from app import create_app
from setup_log import setup_logging

logger, debug_logger = setup_logging()

app = create_app()
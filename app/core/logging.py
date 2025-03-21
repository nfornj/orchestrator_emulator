import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Console handler with JSON formatting
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    handler.setFormatter(formatter)
    
    root_logger.addHandler(handler)
    
    # Suppress noisy loggers
    logging.getLogger('azure').setLevel(logging.WARNING)
    
    return root_logger

# Initialize logger
logger = setup_logging() 
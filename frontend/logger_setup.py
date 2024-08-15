import logging
from logging.handlers import RotatingFileHandler

# Variable to easily turn logging on or off
LOGGING_ENABLED = True  # Set this to False to disable logging

if LOGGING_ENABLED:
    # Configure the logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)  # Set the log level to DEBUG to capture all types of log messages

    # Create a rotating file handler to log messages to a file
    # RotatingFileHandler parameters:
    # - 'app.log': The log file name
    # - maxBytes=5*1024*1024: Maximum file size of 5MB before rotating
    # - backupCount=0: No backup files are kept, overwriting the file when maxBytes is exceeded
    file_handler = RotatingFileHandler('app.log', maxBytes=5*1024*1024, backupCount=0)
    file_handler.setLevel(logging.DEBUG)

    # Create a console handler to log messages to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # Create a formatter and set it for both handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
else:
    # If logging is disabled, create a dummy logger that does nothing
    logger = logging.getLogger(__name__)
    logger.addHandler(logging.NullHandler())
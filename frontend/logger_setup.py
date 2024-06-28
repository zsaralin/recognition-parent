import logging

# Configure the logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set the log level to DEBUG to capture all types of log messages

# Create a file handler to log messages to a file
file_handler = logging.FileHandler('app.log')
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

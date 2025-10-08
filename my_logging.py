import logging
import os

def setup_logging(app_name, base_dir="~/projects"):
    # Define the base directory
    base_dir = os.path.expanduser(base_dir)
    
    # Create the logs directory if it doesn't exist
    logs_dir = os.path.join(base_dir, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Create a subdirectory for the app
    app_logs_dir = os.path.join(logs_dir, app_name)
    if not os.path.exists(app_logs_dir):
        os.makedirs(app_logs_dir)
    
    # Set up logging to file (log file is named after the app)
    log_file = os.path.join(app_logs_dir, f"{app_name}.log")

    # Create a logger
    logger = logging.getLogger(app_name)
    logger.setLevel(logging.INFO)  # Set default level to INFO

    # Create handlers for both file and console logging
    file_handler = logging.FileHandler(log_file)
    console_handler = logging.StreamHandler()

    # Set log format
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

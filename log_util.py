import os
import logging

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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Optional: Also log to console
        ]
    )

    return log_file

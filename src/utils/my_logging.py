# utils/my_logging.py
import logging
import os

def setup_logging(app_name, base_dir="~/projects"):
    base_dir = os.path.expanduser(base_dir)
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    app_logs_dir = os.path.join(logs_dir, app_name)
    os.makedirs(app_logs_dir, exist_ok=True)

    log_file = os.path.join(app_logs_dir, f"{app_name}.log")

    logger = logging.getLogger(app_name)
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file)
    console_handler = logging.StreamHandler()

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # avoid duplicate handlers on reruns
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    logger.debug("Logger initialized with DEBUG level")
    return logger

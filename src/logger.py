import os
import json
import logging
from datetime import datetime

_loggers: dict = {}
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")


def get_logger(session_id: str | None = None) -> logging.Logger:
    os.makedirs(LOGS_DIR, exist_ok=True)
    key = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    if key in _loggers:
        return _loggers[key]

    logger = logging.getLogger(f"music4u.{key}")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        path = os.path.join(LOGS_DIR, f"session_{key}.log")
        fh = logging.FileHandler(path, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(fh)

    _loggers[key] = logger
    return logger


def log_event(logger: logging.Logger, event: str, data: dict) -> None:
    logger.info(f"{event} | {json.dumps(data, ensure_ascii=False, default=str)}")

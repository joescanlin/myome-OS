"""Logging configuration for Myome"""

import logging
import sys
from typing import Literal

from myome.core.config import settings


def setup_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO",
) -> logging.Logger:
    """Configure application logging"""

    log_level = logging.DEBUG if settings.debug else getattr(logging, level)

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # Root logger
    root_logger = logging.getLogger("myome")
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return root_logger


logger = setup_logging()

"""Type stub exposing root-level monitoring under the src package for static type checkers."""
from monitoring import (
    get_logger as get_logger,
    log_event as log_event,
    LOGGER_NAME as LOGGER_NAME,
)

__all__ = [
    "get_logger",
    "log_event",
    "LOGGER_NAME",
]

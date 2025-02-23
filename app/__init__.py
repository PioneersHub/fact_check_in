__version__ = "0.6.1"

import logging
import os

import structlog

from app.config import TOKEN
from app.middleware.interface import Interface

# Configure standard logging to route through structlog
logging.basicConfig(
    level=logging.DEBUG,  # Set the desired log level
    format="%(message)s",
    force=True,  # Ensure existing logging configs are overridden
)


os.environ["FORCE_COLOR"] = "1"
logging.getLogger("urllib3").setLevel(logging.CRITICAL + 1)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="%Y%m%dT%H%M%S", utc=True),
        structlog.dev.ConsoleRenderer(),  # Ensure ConsoleRenderer is used
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),  # Use stdlib logging
    cache_logger_on_first_use=True,
)

log = structlog.get_logger()
log.info("Logging configured")

# if the API token is not set, we are in fake mode by default
in_dummy_mode = False
if not TOKEN:
    log.info("Activated dummy mode, no Token set")
    in_dummy_mode = True
elif os.environ.get("FAKE_CHECK_IN_TEST_MODE"):
    log.info("Activated dummy mode as requested via environment")
    in_dummy_mode = True
else:
    log.info("Using real API token")
interface = Interface(in_dummy_mode=in_dummy_mode)


def reset_interface(dummy_mode=True):
    global interface  # noqa: PLW0603
    interface = None
    interface = Interface(in_dummy_mode=dummy_mode)


__all__ = ["log", "interface", "in_dummy_mode", "reset_interface"]

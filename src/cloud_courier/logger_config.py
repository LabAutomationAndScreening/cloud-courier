import socket
from logging.config import dictConfig
from pathlib import Path

import structlog

SUBSYSTEM_NAME = "courier"


def configure_logging(
    *, log_filename_prefix: str = "logs/cloud-courier-", log_level: str = "INFO", suppress_console_logging: bool = False
):
    """Configure structlog to output both to the console and JSON to a file.

    This also configures stdlib logging to also use the same structlog formatters using details found here.
    https://www.structlog.org/en/stable/standard-library.html#rendering-using-structlog-based-formatters-within-logging
    """
    _ = structlog.contextvars.bind_contextvars(
        **{
            "event.dataset": "cloud-courier",
            "subsystem": SUBSYSTEM_NAME,
            "host.name": socket.gethostname(),
            "host.ip": socket.gethostbyname(socket.gethostname()),
        }
    )

    shared_processors = [
        # Merges context vars
        structlog.contextvars.merge_contextvars,
        # Add the log level to the event dict.
        structlog.stdlib.add_log_level,
        # Add the name of the logger to event dict.
        structlog.stdlib.add_logger_name,
        # Add extra attributes of `logging.LogRecord` objects to the event dictionary.
        structlog.stdlib.ExtraAdder(),
        # Add a timestamp in ISO 8601 format.
        structlog.processors.TimeStamper(fmt="iso"),
        # If some value is in bytes, decode it to a Unicode str.
        structlog.processors.UnicodeDecoder(),
        # Perform %-style formatting.
        structlog.stdlib.PositionalArgumentsFormatter(),
        # If the "stack_info" key in the event dict is true, remove it and
        # render the current stack trace in the "stack" key.
        structlog.processors.StackInfoRenderer(),
    ]

    # based on https://www.structlog.org/en/stable/standard-library.html
    internal_processors = [
        # If log level is too low, abort pipeline and throw away log entry. This only works for structlog logging and not stdlib
        structlog.stdlib.filter_by_level,
        *shared_processors,
        # Transform event dict into `logging.Logger` method arguments.
        # "event" becomes "msg" and the rest is passed as a dict in
        # "extra". IMPORTANT: This means that the standard library MUST
        # render "extra" for the context to appear in log entries! See
        # warning below.
        structlog.stdlib.render_to_log_kwargs,
    ]

    structlog.configure(
        cache_logger_on_first_use=True,
        wrapper_class=structlog.make_filtering_bound_logger(20),
        processors=internal_processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    log_filename = f"{log_filename_prefix}{SUBSYSTEM_NAME}.log"
    directory = Path(log_filename).parent
    Path(directory).mkdir(parents=True, exist_ok=True)

    # Defaults to 25MB
    log_size_max_bytes = 25 * 1024 * 1024

    json_processors = [
        *shared_processors,
        structlog.processors.ExceptionRenderer(structlog.tracebacks.ExceptionDictTransformer()),
        structlog.processors.EventRenamer(to="message"),
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.processors.JSONRenderer(),
    ]
    console_processors = [
        *shared_processors,
        structlog.processors.EventRenamer(to="message"),
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.dev.ConsoleRenderer(colors=True),
    ]
    handlers = ["file"]
    if not suppress_console_logging:
        handlers.append("default")
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": json_processors,
                    "foreign_pre_chain": shared_processors,
                },
                "colored": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": console_processors,
                    "foreign_pre_chain": shared_processors,
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "colored",
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": log_filename,
                    "formatter": "json",
                    "maxBytes": log_size_max_bytes,
                    "backupCount": 5,
                },
            },
            "loggers": {
                "": {
                    "handlers": handlers,
                    "level": log_level,
                    "propagate": True,
                },
            },
        }
    )

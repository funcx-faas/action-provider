from datetime import datetime, timezone
import logging
import logging.config
import structlog
import typing as t
import typing_extensions as te
import uuid
from flask import request, g

logger = structlog.getLogger(__name__)


def init_logging(
    log_level: t.Optional[str] = None,
    log_format: te.Literal["json", "console"] = "console",
):
    """
    This function configures the root logger to run in "console" or "json" mode.
    Whenever a module creates a new logger via logging.getLogger(__name__) or
    via structlog.get_logger(__name__), it will inherit these settings.
    """
    shared_processors: t.List[t.Callable] = [
        structlog.threadlocal.merge_threadlocal,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
    ]
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(),
                "foreign_pre_chain": shared_processors,
            },
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
                "foreign_pre_chain": shared_processors,
            },
        },
        "handlers": {
            "default": {
                "formatter": log_format
                if log_format.lower() in ["console", "json"]
                else "console",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "null": {
                "class": "logging.NullHandler",
            },
        },
        "loggers": {
            "werkzeug": {"handlers": ["null"], "propagate": False},
            "gunicorn": {
                "handlers": ["default"],
                "level": log_level.upper() if log_level else "INFO",
                "propagate": False,
            },
            "globus_sdk": {
                "handlers": ["default"],
                "level": "WARNING",
                "propagate": False,
            },
            "globus_action_provider_tools": {
                "handlers": ["default"],
                "level": log_level.upper() if log_level else "INFO",
                "propagate": False,
            },
            "funcx_action_provider": {
                "handlers": ["default"],
                "level": log_level.upper() if log_level else "INFO",
                "propagate": False,
            },
        },
    }
    logging.config.dictConfig(logging_config)

    structlog.configure(
        logger_factory=structlog.stdlib.LoggerFactory(),
        processors=shared_processors
        + [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        cache_logger_on_first_use=True,
    )

    logger.info("Initialized logging", format=log_format, log_level=log_level)


def set_request_info_for_logging():
    """
    Bind request-specific data to every logging call and log that will be
    emitted.
    """
    request_start_time = datetime.now(timezone.utc)
    debug_id = str(uuid.uuid4())

    if isinstance(request.access_route, list) and len(request.access_route) > 0:
        peer = request.access_route[0]
    else:
        peer = f"Unknown: {request.access_route}"

    structlog.threadlocal.clear_threadlocal()
    structlog.threadlocal.bind_threadlocal(
        debug_id=debug_id,
        action_provider=request.blueprint,
        peer=peer,
        request_view=request.endpoint,
        request_method=request.method,
        request_path=request.path,
        request_params=request.args.to_dict(),
        request_start_time=request_start_time.isoformat(),
    )
    g.request_start_time = request_start_time
    g.debug_id = debug_id


def log_request_time(error):
    """
    Regardless of if an exception was raised, this will calculate the length of
    time spent in the view and produce one last log with that data.
    """
    request_end_time = datetime.now(timezone.utc)
    total_request_time = (request_end_time - g.request_start_time).total_seconds()
    logger.info(
        "API request complete.",
        **{
            "request_end_time": str(request_end_time),
            "total_request_time_s": total_request_time,
        },
    )

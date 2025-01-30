import logging
import os
import sys

import structlog


def configure_logger(verbosity: int) -> None:
    """Configure structlog-based logging.

    :param verbosity: The verbosity level of the logger.
    """
    # Disable faker logging.
    logging.getLogger("faker").setLevel(logging.ERROR)

    processors = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if verbosity == 0:
        level = logging.WARNING
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG

        processors.append(
            structlog.processors.CallsiteParameterAdder(
                [
                    structlog.processors.CallsiteParameter.MODULE,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                ]
            )
        )

    if sys.stderr.isatty() and not os.environ.get("NO_COLOR"):
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors += [
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        logger_factory=structlog.PrintLoggerFactory(),
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
    )

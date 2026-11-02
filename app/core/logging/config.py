import logging
import logging.config

from app.core.logging.context import request_id_ctx


class RequestIDFilter(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


def setup_logging() -> None:

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,

        "filters": {
            "request_id": {
                "()": RequestIDFilter,
            },
        },

        "formatters": {
            "standard": {
                "format": (
                    "%(asctime)s | "
                    "%(levelname)s | "
                    "%(name)s | "
                    "RequestID=%(request_id)s | "
                    "%(message)s"
                ),
            },
        },

        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "standard",
                "filters": ["request_id"],
            },
        },

        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
    })
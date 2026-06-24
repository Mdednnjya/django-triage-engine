import json
import logging
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_EXTRA_FIELDS = ("status", "duration_ms", "error", "transaction_id", "count")


class JsonFormatter(logging.Formatter):

    def format(self, record):

        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id_var.get(),
            "event": record.getMessage(),
        }

        for field in _EXTRA_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)

        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)

        return json.dumps(payload)

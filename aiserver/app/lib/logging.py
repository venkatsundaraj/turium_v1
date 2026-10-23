import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

# Set per request by the middleware in main.py so every log line can be correlated.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    """One JSON object per line. Pass structured fields via `extra={"fields": {...}}`."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "request_id": request_id_var.get(),
            **getattr(record, "fields", {}),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # Uvicorn's access log duplicates our request log; noisy client libs stay at WARNING.
    logging.getLogger("uvicorn.access").disabled = True
    for name in ("httpx", "httpx2", "openai", "trafilatura"):
        logging.getLogger(name).setLevel(logging.WARNING)

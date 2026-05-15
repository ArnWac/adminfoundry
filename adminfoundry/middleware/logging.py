import asyncio
import json
import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("adminfoundry.access")

_JSON_SKIP = frozenset({
    "msg", "args", "levelname", "levelno", "name", "filename", "module",
    "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created",
    "msecs", "relativeCreated", "thread", "threadName", "processName",
    "process", "message", "taskName", "pathname",
})


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        log: dict = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
        }
        for k, v in record.__dict__.items():
            if k not in _JSON_SKIP and not k.startswith("_"):
                log[k] = v
        if record.exc_info:
            log["exc"] = self.formatException(record.exc_info)
        return json.dumps(log, default=str)


def configure_json_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    if not root.level:
        root.setLevel(logging.INFO)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        response.headers["X-Request-ID"] = request_id

        runtime = getattr(getattr(request.app, "state", None), "adminfoundry", None)
        if runtime is not None:
            asyncio.create_task(runtime.event_bus.emit("request_finished", {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            }))

        return response

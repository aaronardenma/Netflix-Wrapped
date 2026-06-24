import json
import logging
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone


request_id_context = ContextVar("request_id", default="-")


class RequestContextFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_context.get()
        return True


class JsonLogFormatter(logging.Formatter):
    reserved = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }

    def format(self, record):
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        for key, value in record.__dict__.items():
            if key not in self.reserved and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("api.requests")

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_context.set(request_id)
        request.request_id = request_id
        start = time.perf_counter()
        response = None

        try:
            response = self.get_response(request)
            return response
        except Exception:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            self.logger.exception(
                "request failed",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "status_code": 500,
                    "elapsed_ms": elapsed_ms,
                },
            )
            raise
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            if response is not None:
                response["X-Request-ID"] = request_id
                level = logging.WARNING if response.status_code >= 400 else logging.INFO
                self.logger.log(
                    level,
                    "request completed",
                    extra={
                        "method": request.method,
                        "path": request.path,
                        "status_code": response.status_code,
                        "elapsed_ms": elapsed_ms,
                    },
                )
            request_id_context.reset(token)

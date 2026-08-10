from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Mapping
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("complexity_library")
_SECRET_KEY_PATTERN = re.compile(r"(key|secret|token|password|authorization)", re.IGNORECASE)


def redact(value: Any) -> Any:
    """Remove secret-looking fields and keep logging code/prompt-safe by default."""
    if isinstance(value, Mapping):
        return {key: "[REDACTED]" if _SECRET_KEY_PATTERN.search(str(key)) else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def log_event(event: str, **fields: Any) -> None:
    logger.info("%s %s", event, redact(fields))


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log_event("http.request.failed", request_id=request_id, method=request.method, path=request.url.path)
            raise
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        log_event("http.request.completed", request_id=request_id, method=request.method, path=request.url.path, status_code=response.status_code, duration_ms=duration_ms)
        return response

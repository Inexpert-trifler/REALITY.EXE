import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP request lifecycle and execution latency."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start_time = time.time()
        request_id = getattr(request.state, "request_id", "unknown")

        logger.info(
            f"Started {request.method} '{request.url.path}'",
            extra={
                "event": "request_start",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )

        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            logger.info(
                f"Completed {request.method} '{request.url.path}' -> Status {response.status_code}",
                extra={
                    "event": "request_completion",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "latency": round(process_time, 2),
                },
            )
            return response
        except Exception as exc:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"Failed {request.method} '{request.url.path}': {exc}",
                extra={
                    "event": "critical_error",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "latency": round(process_time, 2),
                },
            )
            raise

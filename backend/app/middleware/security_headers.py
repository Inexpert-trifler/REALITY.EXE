"""Security headers middleware.

Adds defensive HTTP headers to every response.  These headers instruct
browsers to enable built-in protections against common attack classes.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every HTTP response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # Prevent MIME-type sniffing (guards against polyglot file attacks)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Block framing to prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Control how much referrer info is sent cross-origin
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Disable browser features not needed by this API
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # HSTS — only set on HTTPS; the check is best-effort without a
        # reliable is-HTTPS signal at middleware level
        if request.headers.get("x-forwarded-proto") == "https" or str(request.url).startswith(
            "https://"
        ):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette_context import context
from structlog.contextvars import bind_contextvars, clear_contextvars


class LoggingMiddleware(BaseHTTPMiddleware):
    # Adapted from https://starlette-context.readthedocs.io/en/latest/example.html

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        clear_contextvars()
        bind_contextvars(correlation_id=context["X-Correlation-ID"], request_id=context["X-Request-ID"])
        return await call_next(request)


# see docs: https://starlette-context.readthedocs.io/en/latest/plugins.html#example-usage
middleware = []

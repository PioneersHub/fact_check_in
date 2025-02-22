from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette_context import context, plugins
from starlette_context.middleware import ContextMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class LoggingMiddleware(BaseHTTPMiddleware):
    # Adapted from https://starlette-context.readthedocs.io/en/latest/example.html

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        clear_contextvars()
        bind_contextvars(correlation_id=context["X-Correlation-ID"], request_id=context["X-Request-ID"])
        response = await call_next(request)
        return response


# see docs: https://starlette-context.readthedocs.io/en/latest/plugins.html#example-usage
middleware = [
    # Middleware(ContextMiddleware, plugins.RequestIdPlugin(), plugins.CorrelationIdPlugin()),
    # Middleware(LoggingMiddleware),
]

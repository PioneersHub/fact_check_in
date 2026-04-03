import logging
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.auth import verify_token
from app.config import CONFIG
from app.middleware import middleware
from app.routers import routers
from app.routers.common import refresh_all


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    # Startup code
    refresh_all()
    # Run Pretix validation and load add-on statistics if using Pretix backend
    try:
        from app.pretix.validation import validate_pretix_mappings

        validate_pretix_mappings()
    except Exception:  # broad catch intentional during startup
        logger = logging.getLogger("uvicorn.error")
        logger.exception("Failed to validate Pretix mappings")

    try:
        from app.pretix.addon_stats import load_addon_statistics

        load_addon_statistics()
    except Exception:  # broad catch intentional during startup
        logger = logging.getLogger("uvicorn.error")
        logger.exception("Failed to load add-on statistics")

    logger = logging.getLogger("uvicorn.error")
    # Try to get the actual port from uvicorn server

    # Detect port from command line args or environment
    port = "8000"  # Default uvicorn port
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            port = sys.argv[i + 1]
            break
        elif arg.startswith("--port="):
            port = arg.split("=")[1]
            break

    # Could also be set via environment
    if os.environ.get("PORT"):
        port = os.environ.get("PORT")

    from app.auth import get_auth_config

    auth_config = get_auth_config()
    if auth_config.enabled:
        logger.info(
            "OAuth2 authentication is ENABLED (issuer: %s)",
            auth_config.issuer_url,
        )
    else:
        logger.warning("OAuth2 authentication is DISABLED. Set OIDC_ISSUER_URL env var to enable")

    logger.info("\n" + "=" * 60)
    logger.info(f"🚀 {CONFIG.PROJECT_NAME} Ready!")
    logger.info("=" * 60)
    logger.info("📚 API Documentation (Swagger UI):")
    logger.info(f"   http://localhost:{port}/docs")
    logger.info("=" * 60)
    yield
    # Shutdown code
    logger.info("shutting down")


app = FastAPI(title=CONFIG.PROJECT_NAME, middleware=middleware, lifespan=lifespan)

# routers are dynamically collected in routers.__init__.py file
# All router endpoints require a valid OAuth2 Bearer token when OIDC_ISSUER_URL is set.
# Healthcheck endpoints defined directly on the app remain public.
for router in sorted(routers, key=lambda x: x.router.tags[0]):
    app.include_router(router.router, dependencies=[Depends(verify_token)])


# Report validation errors, see https://stackoverflow.com/a/62937228
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):  # noqa: ARG001
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "Error": "Validation error."}),
    )


@app.get("/")
@app.get("/healthcheck/alive")
async def healthcheck():
    """Check if the service is alive."""
    return {"alive": True}


if __name__ == "__main__":
    import sys

    # Parse command line arguments for host and port
    host = CONFIG.APP.HOST
    port = CONFIG.APP.PORT

    for i, arg in enumerate(sys.argv):
        if arg == "--host" and i + 1 < len(sys.argv):
            host = sys.argv[i + 1]
        elif arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])

    # Custom startup message
    # Convert 0.0.0.0 to localhost for display
    display_host = "localhost" if host == "0.0.0.0" else host
    print(f"\n{'=' * 60}")  # noqa: T201
    print(f"Starting {CONFIG.PROJECT_NAME}")  # noqa: T201
    print(f"{'=' * 60}")  # noqa: T201
    print(f"Server:     http://{display_host}:{port}")  # noqa: T201
    print(f"API Docs:   http://{display_host}:{port}/docs")  # noqa: T201
    print(f"ReDoc:      http://{display_host}:{port}/redoc")  # noqa: T201
    print(f"OpenAPI:    http://{display_host}:{port}/openapi.json")  # noqa: T201
    print(f"{'=' * 60}\n")  # noqa: T201

    uvicorn.run(
        app,
        host=host,
        port=port,
    )

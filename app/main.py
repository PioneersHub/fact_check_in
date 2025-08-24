import logging
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.config import CONFIG
from app.middleware import middleware
from app.routers import routers
from app.routers.common import refresh_all


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    # Startup code
    refresh_all()
    # Run Pretix validation if using Pretix backend
    try:
        # make sure to use lazy import
        from app.pretix.validation import validate_pretix_mappings  # noqa: PLC0415

        validate_pretix_mappings()
    except Exception as e:
        logger = logging.getLogger("uvicorn.error")
        logger.error(f"Failed to validate Pretix mappings: {e}")

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
for router in sorted(routers, key=lambda x: x.router.tags[0]):
    app.include_router(router.router)


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
    """
    Simple endpoint to check if the service is alive
    """
    content = {"alive": True}
    return content


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
    print(f"\n{'=' * 60}")
    print(f"Starting {CONFIG.PROJECT_NAME}")
    print(f"{'=' * 60}")
    print(f"Server:     http://{display_host}:{port}")
    print(f"API Docs:   http://{display_host}:{port}/docs")
    print(f"ReDoc:      http://{display_host}:{port}/redoc")
    print(f"OpenAPI:    http://{display_host}:{port}/openapi.json")
    print(f"{'=' * 60}\n")

    uvicorn.run(
        app,
        host=host,
        port=port,
    )

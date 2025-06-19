from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.config import CONFIG
from app.middleware import middleware
from app.routers import routers
from app.routers.tickets import refresh_all


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    # Startup code
    refresh_all()

    # Print startup info
    import logging

    logger = logging.getLogger("uvicorn.error")
    logger.info("=" * 60)
    logger.info(f"🚀 {CONFIG.PROJECT_NAME} Ready!")
    logger.info("=" * 60)
    logger.info("📚 API Documentation: /docs")
    logger.info("📊 OpenAPI Schema: /openapi.json")
    logger.info("🔍 ReDoc: /redoc")
    logger.info("=" * 60)

    yield
    # Shutdown code
    refresh_all()


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
    print(f"\n{'=' * 60}")
    print(f"Starting {CONFIG.PROJECT_NAME}")
    print(f"{'=' * 60}")
    print(f"Server:     http://{host}:{port}")
    print(f"API Docs:   http://{host}:{port}/docs")
    print(f"OpenAPI:    http://{host}:{port}/openapi.json")
    print(f"{'=' * 60}\n")

    uvicorn.run(
        app,
        host=host,
        port=port,
    )

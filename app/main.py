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
    # Startup code (if any)
    refresh_all()
    yield
    refresh_all()
    # Shutdown code (if any)


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
    uvicorn.run(
        app,
        host=CONFIG.APP.HOST,
        port=CONFIG.APP.PORT,
    )

import pathlib

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import ValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import CONFIG
from app.middleware import middleware
from app.routers import routers
from app.routers.tickets import refresh_all

app = FastAPI(title=CONFIG.PROJECT_NAME, middleware=middleware)

p = pathlib.Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=p, html=True), name="static")

# routers are dynamically collected in routers.__init__.py file
for router in sorted(routers, key=lambda x: x.router.tags[0]):
    app.include_router(router.router)

# Report validation errors, see https://stackoverflow.com/a/62937228
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
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


@app.on_event("startup")  # new
async def app_startup():
    await refresh_all()


# noinspection PyUnusedLocal,PyShadowingNames
def setup(app):
    # do not remove, required for sphinx to generate OpenAPI docs
    # https://stackoverflow.com/questions/18356226/how-to-use-python-functions-in-conf-py-file-in-sphinx
    return


if __name__ == "__main__":
    import os
    uvicorn.run(app, host="0.0.0.0", port=8080)

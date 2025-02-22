import uvicorn

from app.config import CONFIG
from app.main import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=CONFIG.APP.HOST,
        port=CONFIG.APP.PORT,
    )

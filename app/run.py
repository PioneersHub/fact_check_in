import uvicorn

from app.config import CONFIG
from app.main import app

if __name__ == "__main__":
    import os
    uvicorn.run(app, host="0.0.0.0", port=CONFIG["PORT"])

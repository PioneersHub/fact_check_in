import socket
from pathlib import Path

from omegaconf import OmegaConf

project_root = Path(__file__).resolve().parents[2]


CONFIG = OmegaConf.load(Path(__file__).parent.resolve() / "base.yml")

if not CONFIG.APP.get("HOST"):
    CONFIG.APP.HOST = socket.gethostname()

datadir = Path(__file__).parents[1] / "_data"
datadir.mkdir(exist_ok=True)

static = Path(__file__).parent.parent / "static"
static.mkdir(exist_ok=True)


CONFIG["datadir"] = datadir

account_slug = CONFIG["account_slug"]
event_slug = CONFIG["event_slug"]

token_path = project_root / "_private/TOKEN.txt"
if not token_path.exists():
    token_path.open("w").write("PUT-YOUR-TITO-TOKEN-HERE")
TOKEN = token_path.open().read()

__all__ = ["CONFIG", "TOKEN", "event_slug", "account_slug"]

import os
import socket
from pathlib import Path

from dotenv import dotenv_values, load_dotenv
from omegaconf import OmegaConf

project_root = Path(__file__).resolve().parents[2]

CONFIG = OmegaConf.load(Path(__file__).parent.resolve() / "base.yml")

if not CONFIG.APP.get("HOST"):
    CONFIG.APP.HOST = socket.gethostname()


def reload_env():
    """Force reload .env variables by clearing existing ones."""
    env_vars = dotenv_values()
    for key in env_vars:
        if key in os.environ:
            del os.environ[key]  # Clear existing env vars
    load_dotenv(override=True)


reload_env()

CONFIG["account_slug"] = os.environ.get("ACCOUNT_SLUG")
CONFIG["event_slug"] = os.environ.get("EVENT_SLUG")

# for convenience
account_slug = CONFIG["account_slug"]
event_slug = CONFIG["event_slug"]

TOKEN = os.getenv("TITO_TOKEN")
if not TOKEN:
    print("no token found in environment, trying config")

__all__ = ["CONFIG", "TOKEN", "event_slug", "account_slug", "project_root"]

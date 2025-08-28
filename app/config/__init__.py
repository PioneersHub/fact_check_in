import os
import socket
from pathlib import Path

from dotenv import dotenv_values, load_dotenv
from omegaconf import OmegaConf

project_root = Path(__file__).resolve().parents[2]

BASE_CONFIG = OmegaConf.load(Path(__file__).parent.resolve() / "base.yml")
LOCAL_CONFIG = OmegaConf.load(Path(__file__).parents[2].resolve() / "event_config.yml")

CONFIG = OmegaConf.merge(BASE_CONFIG, LOCAL_CONFIG)

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

# Allow environment variables to override config
if os.environ.get("TICKETING_BACKEND"):
    CONFIG["TICKETING_BACKEND"] = os.environ.get("TICKETING_BACKEND")

# for convenience
account_slug = CONFIG["account_slug"]
event_slug = CONFIG["event_slug"]

TOKEN = None
if CONFIG["TICKETING_BACKEND"] == "tito":
    TOKEN = os.getenv("TITO_TOKEN")
elif CONFIG["TICKETING_BACKEND"] == "pretix":
    TOKEN = os.getenv("PRETIX_TOKEN")

if not TOKEN:
    print("no token found in environment, trying config")

__all__ = ["CONFIG", "TOKEN", "event_slug", "account_slug", "project_root"]

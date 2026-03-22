import os
import socket
from pathlib import Path
from typing import cast

from dotenv import dotenv_values, load_dotenv
from omegaconf import DictConfig, OmegaConf

project_root = Path(__file__).resolve().parents[2]

# The base config is always loaded
BASE_CONFIG = cast(DictConfig, OmegaConf.load(Path(__file__).parent.resolve() / "base.yml"))

# The local config is optional and can override the base config
LOCAL_CONFIG_PATH = Path(__file__).parents[2].resolve() / "event_config.yml"
if LOCAL_CONFIG_PATH.exists():
    LOCAL_CONFIG: DictConfig = cast(DictConfig, OmegaConf.load(LOCAL_CONFIG_PATH))
    CONFIG = cast(DictConfig, OmegaConf.merge(BASE_CONFIG, LOCAL_CONFIG))
else:
    CONFIG = BASE_CONFIG

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
if backend := os.environ.get("TICKETING_BACKEND"):
    CONFIG["TICKETING_BACKEND"] = backend

# for convenience
account_slug = CONFIG["account_slug"]
event_slug = CONFIG["event_slug"]

TOKEN = None
if CONFIG["TICKETING_BACKEND"] == "tito":
    TOKEN = os.getenv("TITO_TOKEN")
elif CONFIG["TICKETING_BACKEND"] == "pretix":
    TOKEN = os.getenv("PRETIX_TOKEN")

if not TOKEN:
    print("no token found in environment, trying config")  # noqa: T201

__all__ = ["CONFIG", "TOKEN", "account_slug", "event_slug", "project_root"]

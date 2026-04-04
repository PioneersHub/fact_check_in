import os
from urllib.parse import urljoin

# Must be set before any test module triggers app imports at collection time
os.environ["FAKE_CHECK_IN_TEST_MODE"] = "1"

import pytest
import requests
from fastapi.testclient import TestClient


class LiveServerSession(requests.Session):
    """Allow execution of tests against a separately deployed client, e.g. for smoke tests during deployment.
    Taken from https://github.com/psf/requests/issues/2554#issuecomment-109341010.
    """

    def __init__(self, prefix_url):
        self.prefix_url = prefix_url
        super().__init__()

    def request(self, method, url, *args, **kwargs):
        url = urljoin(self.prefix_url, url)
        return super().request(method, url, *args, **kwargs)


@pytest.fixture(scope="session")
def app_client(_set_tito_for_unit_tests):  # noqa: ARG001
    from app import main
    from app.config import CONFIG

    # Environment variable is set in the Release-Pipeline or in ci\execute_tests.bat.
    USE_LIVE_SERVICE = os.environ.get("Test_UseLiveService", "False").strip().lower() in ("true", "1")  # noqa: N806, SIM112
    if USE_LIVE_SERVICE:
        # During deployment the port is configured in the pipeline (Variable 'Application.Port.Active')
        # and not directly from the config.
        # Similar for host as the pipeline agent is on a remote server.
        port = os.environ.get("Application_Port_Active", CONFIG.APP.PORT)  # noqa: SIM112
        host = os.environ.get("Server_App", CONFIG.APP.HOST)  # noqa: SIM112
        url_base = f"http://{host}:{port}"

        print(f"Testing against service at {url_base}")
        tc = LiveServerSession(url_base)
    else:
        tc = TestClient(main.app, raise_server_exceptions=True)
    return tc


@pytest.fixture(scope="session")
def _set_tito_for_unit_tests():
    """Force tito backend before any test triggers app.main import.

    app/config/__init__.py calls reload_env() with load_dotenv(override=True),
    which reads TICKETING_BACKEND from .env (pretix) and overrides any env var
    set before the import. This session fixture re-asserts tito AFTER config is
    loaded and BEFORE the router module first runs (router runs on first
    `from app.main import app`).
    """
    from app.config import CONFIG

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("TICKETING_BACKEND", "tito")
        CONFIG["TICKETING_BACKEND"] = "tito"
        yield


@pytest.fixture(autouse=True)
def _clear_oidc_env(monkeypatch):
    """Ensure OIDC env vars are absent and auth config cache is reset.

    Without clearing the lru_cache, a cached AuthConfig from a previous test
    (e.g. test_auth.py's auth_client) persists and enables OAuth2 for later
    tests that don't expect it.
    """
    from app.auth import get_auth_config

    monkeypatch.delenv("OIDC_ISSUER_URL", raising=False)
    monkeypatch.delenv("OIDC_AUDIENCE", raising=False)
    monkeypatch.delenv("OIDC_ALGORITHMS", raising=False)
    get_auth_config.cache_clear()


@pytest.fixture(autouse=True)
def reset_backend_cache(monkeypatch):
    """Reset the backend cache before each test to ensure proper isolation."""
    from app import reset_interface
    from app.config import CONFIG
    from app.ticketing import backend as backend_module

    # Save original CONFIG value
    original_config_backend = CONFIG.get("TICKETING_BACKEND")

    # Clear the cached backend before test
    backend_module._backend = None

    # Reset interface to ensure it uses the correct backend
    reset_interface(dummy_mode=True)

    # reload_env() in app/config/__init__.py may override FAKE_CHECK_IN_TEST_MODE
    # from .env at import time, leaving tito_api.in_dummy_mode as False (it is a
    # module-level bool copy).  Force it to True so the Tito backend never
    # attempts live API calls during tests.
    monkeypatch.setattr("app.tito.tito_api.in_dummy_mode", True)
    monkeypatch.setattr("app.in_dummy_mode", True)

    yield

    # Clear again after test
    backend_module._backend = None

    # Restore CONFIG
    if original_config_backend is not None:
        CONFIG["TICKETING_BACKEND"] = original_config_backend

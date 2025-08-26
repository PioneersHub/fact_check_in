import os
from urllib.parse import urljoin

import pytest
import requests
from fastapi.testclient import TestClient

from app import main
from app.config import CONFIG


class LiveServerSession(requests.Session):
    """
    Allow execution of tests against a separately deployed client, e.g. for smoke tests during deployment.
    Taken from https://github.com/psf/requests/issues/2554#issuecomment-109341010.
    """

    def __init__(self, prefix_url):
        self.prefix_url = prefix_url
        super().__init__()

    def request(self, method, url, *args, **kwargs):
        url = urljoin(self.prefix_url, url)
        return super().request(method, url, *args, **kwargs)


@pytest.fixture(scope="session")
def app_client():
    # Environment variable is set in the Release-Pipeline or in ci\execute_tests.bat.
    USE_LIVE_SERVICE = bool(os.environ.get("Test_UseLiveService", False))  # noqa: N806, SIM112
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
    yield tc


@pytest.fixture(autouse=True, scope="function")
def reset_backend_cache():
    """Reset the backend cache before each test to ensure proper isolation."""
    from app import reset_interface
    from app.ticketing import backend as backend_module

    # Store original environment
    original_backend = os.environ.get("TICKETING_BACKEND")

    # Clear the cached backend before test
    backend_module._backend = None

    # Reset interface to ensure it uses the correct backend
    reset_interface(dummy_mode=True)

    yield

    # Clear again after test
    backend_module._backend = None

    # Restore original environment
    if original_backend is not None:
        os.environ["TICKETING_BACKEND"] = original_backend
    elif "TICKETING_BACKEND" in os.environ:
        del os.environ["TICKETING_BACKEND"]

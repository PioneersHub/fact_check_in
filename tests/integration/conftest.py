"""
Integration test specific configuration.
This overrides the parent conftest.py to disable dummy mode for integration tests.
"""

import os

import pytest


@pytest.fixture(autouse=True, scope="function")
def reset_backend_cache():
    """
    Override the parent conftest's reset_backend_cache to NOT use dummy mode.
    Integration tests need to test against real backends.
    """
    from app.ticketing import backend as backend_module

    # Store original environment
    original_backend = os.environ.get("TICKETING_BACKEND")

    # Clear the cached backend before test
    backend_module._backend = None

    # For integration tests, don't use dummy mode
    # The test itself will handle server setup

    yield

    # Clear again after test
    backend_module._backend = None

    # Restore original environment
    if original_backend is not None:
        os.environ["TICKETING_BACKEND"] = original_backend
    elif "TICKETING_BACKEND" in os.environ:
        del os.environ["TICKETING_BACKEND"]

"""Tests for Pretix integration.

This test module validates the Pretix integration based on the official Pretix API documentation.

Reference URLs for Pretix API documentation:
- Order Positions: https://docs.pretix.eu/en/latest/api/resources/orders.html
  - Contains order position structure with fields like positionid, item, attendee_name, etc.
  - Order status values: 'n' (pending), 'p' (paid), 'e' (expired), 'c' (canceled)

- Items (Products): https://docs.pretix.eu/en/latest/api/resources/items.html
  - Item structure with id, name (multi-lingual), category, default_price, etc.

- Categories: https://docs.pretix.eu/en/latest/api/resources/categories.html
  - Category structure with id, name (multi-lingual), internal_name, position, etc.

- Order Format: https://docs.pretix.eu/en/latest/api/resources/orders.html
  - Order codes consist of A-Z and 0-9 (excluding O and 1)
  - Format example: "ORDER123" with position ID creates reference "ORDER123-1"
"""

from http import HTTPStatus
from threading import Barrier, Thread
from time import sleep
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.pretix import pretix_api

# Constants
PRETIX_REFERENCE_PARTS = 2  # ORDER-POSITION format


class TestPretixIntegration:
    """Test Pretix API integration."""

    def test_determine_activities_from_item(self):
        """Test activity determination from item names."""
        # Test online/remote items
        item = {"name": {"en": "Business Ticket (Online)"}}
        activities = pretix_api.determine_activities_from_item(item)
        assert "remote_sale" in activities
        assert "online_access" in activities

        # Test in-person items
        item = {"name": {"en": "Conference Pass (In-Person)"}}
        activities = pretix_api.determine_activities_from_item(item)
        assert "on_site" in activities
        assert "online_access" in activities

        # Test day pass
        item = {"name": {"en": "Day Pass Monday"}}
        activities = pretix_api.determine_activities_from_item(item)
        assert "on_site" in activities
        assert "seat-person-monday" in activities
        assert "online_access" in activities

        # Test default case
        item = {"name": {"en": "Regular Ticket"}}
        activities = pretix_api.determine_activities_from_item(item)
        assert "on_site" in activities
        assert "online_access" in activities

    @patch("app.pretix.pretix_api.in_dummy_mode", False)
    @patch("requests.get")
    def test_search_reference_format(self, mock_get):
        """Test reference format parsing."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "order": "ABC123",
                    "positionid": 1,
                    "item": 100,
                    "attendee_email": "test@example.com",
                    "attendee_name": "Test User",
                    "order__status": "p",
                },
            ],
        }
        mock_get.return_value = mock_response

        # Test valid reference
        result = pretix_api.search_reference("ABC123-1")
        assert result is not None
        assert len(result) == 1
        assert result[0]["reference"] == "ABC123-1"
        assert result[0]["email"] == "test@example.com"

        # Test invalid reference format
        result = pretix_api.search_reference("INVALID")
        assert result is None or len(result) == 0

    def test_backend_selection(self, monkeypatch):
        """Test that the correct backend is selected based on config."""
        from app.config import CONFIG
        from app.ticketing import backend as backend_module

        # Clear the cached backend
        backend_module._backend = None

        # Test Tito backend
        monkeypatch.setenv("TICKETING_BACKEND", "tito")
        CONFIG.TICKETING_BACKEND = "tito"
        backend = backend_module.get_backend()
        assert backend.__class__.__name__ == "TitoBackend"

        # Clear cache again
        backend_module._backend = None

        # Test Pretix backend
        monkeypatch.setenv("TICKETING_BACKEND", "pretix")
        CONFIG.TICKETING_BACKEND = "pretix"
        backend = backend_module.get_backend()
        assert backend.__class__.__name__ == "PretixBackend"

        # Clear after test
        backend_module._backend = None

    def test_pretix_fake_data_structure(self):
        """Test that Pretix fake data has the correct structure."""
        import json
        from pathlib import Path

        # Load Pretix fake data files
        project_root = Path(__file__).parent.parent
        with (project_root / "tests/test_data/fake_all_sales_pretix.json").open() as f:
            sales = json.load(f)
        with (project_root / "tests/test_data/fake_all_releases_pretix.json").open() as f:
            releases = json.load(f)

        # Test sales structure
        for ref, sale in sales.items():
            # Check reference format
            assert "-" in ref
            parts = ref.split("-")
            assert len(parts) == PRETIX_REFERENCE_PARTS
            # Check valid Pretix order code (no O or 1)
            assert "O" not in parts[0]
            assert "1" not in parts[0]
            assert parts[1].isdigit()

            # Check required fields
            assert "reference" in sale
            assert "email" in sale
            assert "name" in sale
            assert "release_id" in sale
            assert "state" in sale
            assert "_pretix_data" in sale

            # Check Pretix-specific data
            pretix_data = sale["_pretix_data"]
            assert "order" in pretix_data
            assert "positionid" in pretix_data
            assert "secret" in pretix_data
            assert "item" in pretix_data

        # Test releases structure
        for _title, release in releases.items():
            # Check required fields
            assert "id" in release
            assert "title" in release
            assert "activities" in release
            assert "_attributes" in release

            # Check category structure
            if "category" in release:
                cat = release["category"]
                assert "id" in cat
                assert "name" in cat
                assert "internal_name" in cat

            # Check attributes structure
            attrs = release["_attributes"]
            assert "is_speaker" in attrs
            assert "is_sponsor" in attrs
            assert "is_onsite" in attrs
            assert "is_remote" in attrs

    @patch.dict("os.environ", {"TICKETING_BACKEND": "pretix"})
    def test_interface_loads_pretix_fake_data(self):
        """Test that Interface loads Pretix-specific fake data when backend is Pretix."""
        from app import interface, reset_interface
        from app.config import CONFIG

        # Explicitly set the backend in CONFIG (os.environ alone is not enough after .env is loaded)
        CONFIG["TICKETING_BACKEND"] = "pretix"
        # Reset interface with dummy mode
        reset_interface(dummy_mode=True)

        # Check that Pretix data was loaded
        # Pretix references should not contain O or 1
        for ref in interface.all_sales:
            parts = ref.split("-")
            assert "O" not in parts[0]
            assert "1" not in parts[0]

        # Check that categories were loaded
        assert len(interface.categories) > 0

        # Check specific Pretix features
        for sale in interface.all_sales.values():
            assert "_pretix_data" in sale

        # Check that releases have categories
        for release in interface.all_releases.values():
            if release.get("category_id"):
                assert "category" in release


class TestValidateEmailEndpoint:
    """Tests for POST /tickets/validate_email/ on the Pretix backend.

    These tests verify the non-blocking 404 behavior: unknown emails return 404
    immediately and schedule a background refresh, rather than blocking the
    caller for the duration of a full Pretix API refresh (~13 s).
    """

    # A known email from the fake Pretix dataset (tests/test_data/fake_all_sales_pretix.json)
    KNOWN_EMAIL = "angel.hill@example.net"
    UNKNOWN_EMAIL = "nobody@doesnotexist.example"

    @pytest.fixture
    def pretix_client(self):
        """A minimal FastAPI app that only mounts the Pretix router.

        Using a dedicated app (instead of the session-scoped Tito client from
        conftest.py) keeps these tests isolated from backend-switching side
        effects and avoids touching the global app state.
        """
        from app.pretix.router import router

        mini_app = FastAPI()
        mini_app.include_router(router)
        return TestClient(mini_app, raise_server_exceptions=True)

    @pytest.fixture
    def backend_with_email(self):
        """Mock PretixBackend whose email cache contains KNOWN_EMAIL."""
        backend = MagicMock()
        backend.api.interface.valid_emails = {self.KNOWN_EMAIL: {"email": self.KNOWN_EMAIL}}
        return backend

    @pytest.fixture
    def backend_empty(self):
        """Mock PretixBackend with an empty email cache (simulates a cache miss)."""
        backend = MagicMock()
        backend.api.interface.valid_emails = {}
        return backend

    def test_known_email_returns_200(self, pretix_client, backend_with_email):
        """An email present in the cache returns 200 without scheduling a refresh."""
        with (
            patch("app.pretix.router.get_ticketing_backend", return_value=backend_with_email),
            patch("app.routers.common.refresh_all") as mock_refresh,
        ):
            response = pretix_client.post("/tickets/validate_email/", json={"email": self.KNOWN_EMAIL})

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"valid": True}
        mock_refresh.assert_not_called()

    def test_unknown_email_returns_404_immediately(self, pretix_client, backend_empty):
        """An email absent from the cache returns 404 without waiting for a refresh."""
        with patch("app.pretix.router.get_ticketing_backend", return_value=backend_empty), patch("app.routers.common.refresh_all"):
            response = pretix_client.post("/tickets/validate_email/", json={"email": self.UNKNOWN_EMAIL})

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json() == {"valid": False}

    def test_unknown_email_triggers_background_refresh(self, pretix_client, backend_empty):
        """A cache miss schedules exactly one background refresh for the next caller.

        The TestClient runs background tasks synchronously after the response, so
        the mock is called once by the time the assertion runs.
        """
        with (
            patch("app.pretix.router.get_ticketing_backend", return_value=backend_empty),
            patch("app.routers.common.refresh_all") as mock_refresh,
        ):
            pretix_client.post("/tickets/validate_email/", json={"email": self.UNKNOWN_EMAIL})

        mock_refresh.assert_called_once()

    def test_known_email_does_not_trigger_refresh(self, pretix_client, backend_with_email):
        """No background refresh is scheduled when the email IS found in cache."""
        with (
            patch("app.pretix.router.get_ticketing_backend", return_value=backend_with_email),
            patch("app.routers.common.refresh_all") as mock_refresh,
        ):
            pretix_client.post("/tickets/validate_email/", json={"email": self.KNOWN_EMAIL})

        mock_refresh.assert_not_called()


class TestInterfaceCacheInvalidation:
    """Ensure derived caches are rebuilt whenever ``all_sales`` is reassigned.

    The bug this guards against: ``valid_emails`` used to be populated once on
    first access (when the initial startup refresh had loaded the orders) and
    then never rebuilt. Any ticket sold after startup was visible in
    ``valid_order_name_combo`` (rebuilt by the ``all_sales`` setter) but
    absent from ``valid_emails``, so ``/validate_email/`` returned 404 for
    fresh registrations while ``/validate_attendee/`` succeeded on the same
    ticket. The fix extends the setter to rebuild every derived dict; these
    tests pin that behavior.
    """

    @pytest.fixture
    def interface_with_one_sale(self):
        """Return the Interface singleton seeded with one sale.

        We access ``valid_emails`` and ``valid_names`` here to force their
        initial build, so the subsequent ``all_sales`` reassignment is a real
        refresh scenario (caches non-empty from the prior load).
        """
        from app.middleware.interface import Interface

        iface = Interface(in_dummy_mode=False)
        iface.all_sales = {
            "ABC12-1": {
                "reference": "ABC12-1",
                "order": "ABC12",
                "email": "first@example.com",
                "name": "First Person",
                "release_id": 101,
                "state": "complete",
            },
        }
        # Prime the derived caches.
        _ = iface.valid_emails
        _ = iface.valid_names
        _ = iface.valid_order_name_combo
        return iface

    def test_valid_emails_picks_up_new_sale_after_refresh(self, interface_with_one_sale):
        """A sale added after the initial build shows up in ``valid_emails``."""
        iface = interface_with_one_sale
        assert "first@example.com" in iface.valid_emails

        # Simulate a refresh that brings in a new ticket.
        updated = dict(iface.all_sales)
        updated["XYZ98-1"] = {
            "reference": "XYZ98-1",
            "order": "XYZ98",
            "email": "second@example.com",
            "name": "Second Person",
            "release_id": 101,
            "state": "complete",
        }
        iface.all_sales = updated

        assert "second@example.com" in iface.valid_emails
        assert "first@example.com" in iface.valid_emails

    def test_valid_names_picks_up_new_sale_after_refresh(self, interface_with_one_sale):
        """A sale added after the initial build shows up in ``valid_names``."""
        iface = interface_with_one_sale
        assert "FIRST PERSON" in iface.valid_names

        updated = dict(iface.all_sales)
        updated["XYZ98-1"] = {
            "reference": "XYZ98-1",
            "order": "XYZ98",
            "email": "second@example.com",
            "name": "Second Person",
            "release_id": 101,
            "state": "complete",
        }
        iface.all_sales = updated

        assert "SECOND PERSON" in iface.valid_names


class TestRefreshAllLock:
    """Tests for the singleflight guard on refresh_all.

    Without the lock, concurrent threads each see an expired TTL at the same
    instant and each start their own expensive Pretix API refresh. The lock
    ensures only the first thread refreshes; the rest wait and then find the
    timestamp fresh and return without starting another refresh.
    """

    N_THREADS = 5

    def test_concurrent_calls_run_force_refresh_once(self):
        """Concurrent callers trigger force_refresh_all exactly once.

        All threads start at the same instant via a Barrier. The slow inner
        function holds the lock for 0.02 s, giving the other threads time to
        queue up behind it. Without the singleflight guard they would all call
        the inner function; with it, only the first one does.
        """
        import app.routers.common as common_module
        from app.routers.common import refresh_all

        call_count = 0
        barrier = Barrier(self.N_THREADS)

        def slow_force_refresh():
            nonlocal call_count
            call_count += 1
            sleep(0.02)  # hold the lock long enough for other threads to queue up
            return {"message": "ok"}

        # Force TTL expiry so the first call triggers a refresh.
        original_time = common_module._state.last_time
        common_module._state.last_time = 0.0
        try:
            with patch("app.routers.common.force_refresh_all", side_effect=slow_force_refresh):

                def task():
                    barrier.wait()  # release all threads at the same instant
                    refresh_all()

                threads = [Thread(target=task) for _ in range(self.N_THREADS)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
        finally:
            common_module._state.last_time = original_time

        assert call_count == 1

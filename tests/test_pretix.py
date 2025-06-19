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

from unittest.mock import MagicMock, patch

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
                }
            ]
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

    def test_backend_selection(self):
        """Test that the correct backend is selected based on config."""
        import os

        from app.config import CONFIG
        from app.ticketing import backend as backend_module

        # Clear the cached backend
        backend_module._backend = None

        # Test Tito backend
        os.environ["TICKETING_BACKEND"] = "tito"
        CONFIG.TICKETING_BACKEND = "tito"
        backend = backend_module.get_backend()
        assert backend.__class__.__name__ == "TitoBackend"

        # Clear cache again
        backend_module._backend = None

        # Test Pretix backend
        os.environ["TICKETING_BACKEND"] = "pretix"
        CONFIG.TICKETING_BACKEND = "pretix"
        backend = backend_module.get_backend()
        assert backend.__class__.__name__ == "PretixBackend"

        # Reset to original
        backend_module._backend = None
        if "TICKETING_BACKEND" in os.environ:
            del os.environ["TICKETING_BACKEND"]

    def test_pretix_fake_data_structure(self):
        """Test that Pretix fake data has the correct structure."""
        import json
        from pathlib import Path

        # Load Pretix fake data files
        project_root = Path(__file__).parent.parent
        with open(project_root / "tests/test_data/fake_all_sales_pretix.json") as f:
            sales = json.load(f)
        with open(project_root / "tests/test_data/fake_all_releases_pretix.json") as f:
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

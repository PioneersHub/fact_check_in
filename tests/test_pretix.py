"""Tests for Pretix integration."""

from unittest.mock import MagicMock, patch

from app.pretix import pretix_api


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
        from app.config import CONFIG
        from app.ticketing.backend import get_backend

        # Test Tito backend (default)
        CONFIG.TICKETING_BACKEND = "tito"
        backend = get_backend()
        assert backend.__class__.__name__ == "TitoBackend"

        # Test Pretix backend
        CONFIG.TICKETING_BACKEND = "pretix"
        backend = get_backend()
        assert backend.__class__.__name__ == "PretixBackend"

        # Reset to default
        CONFIG.TICKETING_BACKEND = "tito"

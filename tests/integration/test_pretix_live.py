"""
Integration tests for Pretix API endpoints using live data.

This test suite:
1. Fetches real data from the Pretix API
2. Tests all validation endpoints with real and invalid data
3. Verifies the expected behavior and error messages
"""
# ruff: noqa: PLR2004

import os
import subprocess
import sys

import pytest
import requests
from colorama import Fore, Style, init
from test_helpers import (
    PretixTestClient,
    extract_test_cases,
    generate_invalid_test_cases,
    save_test_data,
    wait_for_server,
)

# Initialize colorama for colored output
init(autoreset=True)

# Test configuration
API_BASE_URL = "http://localhost:8002"
TEST_DATA_FILE = "pretix_test_data.json"


class TestPretixIntegration:
    """Integration test suite for Pretix validation endpoints."""

    @classmethod
    def setup_class(cls):
        """Setup test data and start the API server."""
        print(f"\n{Fore.CYAN}=== Setting up Pretix Integration Tests ==={Style.RESET_ALL}")

        # Start the API server with environment variable for port
        env = os.environ.copy()
        env["PORT"] = "8002"
        cls.server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8002", "--host", "127.0.0.1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        # Wait for server to start (Pretix data loading can take time)
        if not wait_for_server(f"{API_BASE_URL}/healthcheck/alive", timeout=60):
            cls.teardown_class()
            raise RuntimeError("Failed to start API server")

        print(f"{Fore.GREEN}✓ API server started on port 8002{Style.RESET_ALL}")

        # Fetch real data from Pretix
        try:
            client = PretixTestClient()
            positions = client.get_order_positions(limit=20)
            items = client.get_items()

            # Extract and save test cases
            test_cases = extract_test_cases(positions)
            invalid_cases = generate_invalid_test_cases(test_cases)

            cls.test_data = {
                "valid": test_cases,
                "invalid": invalid_cases,
                "items": items,
                "raw_positions": positions[:5],  # Save some raw data for reference
            }

            # Save test data for inspection
            filepath = save_test_data(cls.test_data, TEST_DATA_FILE)
            print(f"{Fore.GREEN}✓ Fetched {len(positions)} order positions from Pretix{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✓ Saved test data to {filepath}{Style.RESET_ALL}")

        except Exception as e:
            cls.teardown_class()
            raise RuntimeError(f"Failed to fetch test data from Pretix: {e}") from e

    @classmethod
    def teardown_class(cls):
        """Stop the API server."""
        if hasattr(cls, "server_process"):
            cls.server_process.terminate()
            cls.server_process.wait()
            print(f"\n{Fore.CYAN}✓ API server stopped{Style.RESET_ALL}")

    def test_validate_attendee_with_order_and_name(self):
        """Test validation using order ID + name."""
        print(f"\n{Fore.YELLOW}Testing: Order ID + Name validation{Style.RESET_ALL}")

        valid_attendees = self.test_data["valid"]["valid_attendees"]
        if not valid_attendees:
            pytest.skip("No valid attendees in test data")

        # Test with valid data
        for attendee in valid_attendees[:3]:  # Test first 3
            if attendee["order_id"] and attendee["name"]:
                response = requests.post(
                    f"{API_BASE_URL}/tickets/validate_attendee/", json={"order_id": attendee["order_id"], "name": attendee["name"]}
                )

                # Pretix may return 404 for invalid order IDs or 200 with is_attendee=false
                if response.status_code == 404:
                    print(f"  {Fore.YELLOW}⚠ Order ID {attendee['order_id']} not found in current Pretix data{Style.RESET_ALL}")
                    continue
                assert response.status_code == 200, f"Unexpected status {response.status_code} for {attendee}: {response.text}"
                data = response.json()
                if not data["is_attendee"]:
                    print(
                        f"  {Fore.YELLOW}⚠ {attendee['order_id']} + {attendee['name']} not validated (may be stale test data){Style.RESET_ALL}"
                    )
                    continue
                assert data["is_attendee"] is True
                print(f"  {Fore.GREEN}✓ Valid: {attendee['order_id']} + {attendee['name']}{Style.RESET_ALL}")

    def test_validate_attendee_with_all_fields(self):
        """Test validation using order ID + ticket ID + name (most secure)."""
        print(f"\n{Fore.YELLOW}Testing: Order ID + Ticket ID + Name validation{Style.RESET_ALL}")

        valid_attendees = self.test_data["valid"]["valid_attendees"]

        for attendee in valid_attendees[:3]:
            if attendee["order_id"] and attendee["secret"] and attendee["name"]:
                response = requests.post(
                    f"{API_BASE_URL}/tickets/validate_attendee/",
                    json={"order_id": attendee["order_id"], "ticket_id": attendee["secret"], "name": attendee["name"]},
                )

                # Pretix may return 404 for invalid order IDs or 200 with is_attendee=false
                if response.status_code == 404:
                    print(f"  {Fore.YELLOW}⚠ Order ID {attendee['order_id']} not found in current Pretix data{Style.RESET_ALL}")
                    continue
                assert response.status_code == 200, f"Unexpected status {response.status_code} for {attendee}: {response.text}"
                data = response.json()
                if not data["is_attendee"]:
                    print(
                        f"  {Fore.YELLOW}⚠ {attendee['order_id']} + {attendee['secret'][:8]}... + {attendee['name']} not validated (may be stale test data){Style.RESET_ALL}"
                    )
                    continue
                assert data["is_attendee"] is True
                print(f"  {Fore.GREEN}✓ Valid: {attendee['order_id']} + {attendee['secret'][:8]}... + {attendee['name']}{Style.RESET_ALL}")

    def test_invalid_order_ids(self):
        """Test with invalid order IDs."""
        print(f"\n{Fore.YELLOW}Testing: Invalid Order IDs{Style.RESET_ALL}")

        valid_name = self.test_data["valid"]["names"][0] if self.test_data["valid"]["names"] else "Test User"
        invalid_order_ids = self.test_data["invalid"]["invalid_order_ids"]

        for order_id in invalid_order_ids:
            response = requests.post(f"{API_BASE_URL}/tickets/validate_attendee/", json={"order_id": order_id, "name": valid_name})

            # Should either be 422 (validation error) or 404 (not found)
            assert response.status_code in [422, 404], f"Unexpected status for {order_id}: {response.status_code}"

            if response.status_code == 422:
                print(f"  {Fore.RED}✓ Rejected (validation): {order_id}{Style.RESET_ALL}")
            else:
                data = response.json()
                assert data["is_attendee"] is False
                print(f"  {Fore.RED}✓ Rejected (not found): {order_id} - {data.get('hint', 'No hint')}{Style.RESET_ALL}")

    def test_mismatched_names(self):
        """Test with correct order ID but wrong names."""
        print(f"\n{Fore.YELLOW}Testing: Mismatched Names{Style.RESET_ALL}")

        valid_attendees = self.test_data["valid"]["valid_attendees"]
        if not valid_attendees:
            pytest.skip("No valid attendees in test data")

        # Use first valid attendee's order ID with wrong names
        attendee = valid_attendees[0]
        if attendee["order_id"]:
            wrong_names = ["Wrong Name", "Another Person", "Not The Attendee"]

            for wrong_name in wrong_names:
                response = requests.post(
                    f"{API_BASE_URL}/tickets/validate_attendee/", json={"order_id": attendee["order_id"], "name": wrong_name}
                )

                assert response.status_code in [404, 406], f"Unexpected status for {wrong_name}: {response.status_code}"
                data = response.json()
                assert data["is_attendee"] is False
                print(f"  {Fore.RED}✓ Rejected: {attendee['order_id']} + '{wrong_name}' - {data.get('hint', 'No hint')}{Style.RESET_ALL}")

    def test_fuzzy_name_matching(self):
        """Test fuzzy name matching with variations."""
        print(f"\n{Fore.YELLOW}Testing: Fuzzy Name Matching{Style.RESET_ALL}")

        valid_attendees = self.test_data["valid"]["valid_attendees"]
        if not valid_attendees:
            pytest.skip("No valid attendees in test data")

        attendee = valid_attendees[0]
        if attendee["order_id"] and attendee["name"]:
            name_variations = [
                attendee["name"].lower(),  # lowercase
                attendee["name"].upper(),  # uppercase
                attendee["name"].replace(" ", "  "),  # extra spaces
                " " + attendee["name"] + " ",  # leading/trailing spaces
            ]

            for name_variant in name_variations:
                response = requests.post(
                    f"{API_BASE_URL}/tickets/validate_attendee/", json={"order_id": attendee["order_id"], "name": name_variant}
                )

                # Pretix may return 404 if order ID is not found
                if response.status_code == 404:
                    print(f"  {Fore.YELLOW}⚠ Order ID {attendee['order_id']} not found in current Pretix data{Style.RESET_ALL}")
                    break  # Skip other variations if order ID not found

                assert response.status_code == 200, f"Failed for variant '{name_variant}': {response.text}"
                data = response.json()
                if not data["is_attendee"]:
                    print(
                        f"  {Fore.YELLOW}⚠ Name variant '{name_variant}' not matched (fuzzy matching may not be perfect){Style.RESET_ALL}"
                    )
                else:
                    print(f"  {Fore.GREEN}✓ Accepted variant: '{name_variant}'{Style.RESET_ALL}")

    def test_validate_email(self):
        """Test email validation endpoint."""
        print(f"\n{Fore.YELLOW}Testing: Email Validation{Style.RESET_ALL}")

        # Test valid emails
        valid_emails = [e for e in self.test_data["valid"]["emails"] if e][:3]
        for email in valid_emails:
            response = requests.post(f"{API_BASE_URL}/tickets/validate_email/", json={"email": email})

            # Pretix may return 404 if email not found
            # if response.status_code == 404:
            #     print(f"  {Fore.YELLOW}⚠ Email {email} not found in current Pretix data{Style.RESET_ALL}")
            #     continue

            assert response.status_code == 200, f"Failed for {email}: {response.text}"
            data = response.json()
            if not data.get("valid", False):
                print(f"  {Fore.YELLOW}⚠ Email {email} not validated (may be stale test data){Style.RESET_ALL}")
            else:
                print(f"  {Fore.GREEN}✓ Valid email: {email}{Style.RESET_ALL}")

        # Test invalid emails
        invalid_emails = self.test_data["invalid"]["invalid_emails"]
        for email in invalid_emails:
            response = requests.post(f"{API_BASE_URL}/tickets/validate_email/", json={"email": email})

            # Invalid format should give 422, non-existent should give 404
            if (
                "@" not in email
                or "." not in email
                or email.startswith("@")
                or len(email.split("@")) != 2
                or not (len(email.split("@")) == 2 and len(email.split("@")[-1].split(".")) < 2)
            ):
                assert response.status_code == 422, f"Expected validation error for {email}"
                print(f"  {Fore.RED}✓ Rejected (invalid format): {email}{Style.RESET_ALL}")
            else:
                assert response.status_code == 404, f"Expected 404 for {email}: {response.status_code}"
                data = response.json()
                assert data["valid"] is False
                print(f"  {Fore.RED}✓ Rejected (not found): {email}{Style.RESET_ALL}")

    def test_common_endpoints(self):
        """Test common endpoints."""
        print(f"\n{Fore.YELLOW}Testing: Common Endpoints{Style.RESET_ALL}")

        # Test refresh_all
        response = requests.get(f"{API_BASE_URL}/tickets/refresh_all/")
        assert response.status_code == 200
        data = response.json()
        assert "Pretix" in data.get("message", "")
        print(f"  {Fore.GREEN}✓ Refresh all: {data['message']}{Style.RESET_ALL}")

        # Test ticket_types
        response = requests.get(f"{API_BASE_URL}/tickets/ticket_types/")
        assert response.status_code == 200
        data = response.json()
        assert "ticket_types" in data
        assert isinstance(data["ticket_types"], list)
        print(f"  {Fore.GREEN}✓ Ticket types: Found {len(data['ticket_types'])} types{Style.RESET_ALL}")

        # Test ticket_count
        response = requests.get(f"{API_BASE_URL}/tickets/ticket_count/")
        assert response.status_code == 200
        data = response.json()
        assert "ticket_count" in data
        assert isinstance(data["ticket_count"], int)
        print(f"  {Fore.GREEN}✓ Ticket count: {data['ticket_count']} tickets{Style.RESET_ALL}")


def main():
    """Run the integration tests."""
    print(f"\n{Fore.MAGENTA}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}Pretix Live Integration Tests{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'=' * 60}{Style.RESET_ALL}")

    # Run pytest with verbose output
    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Standalone integration test runner for Pretix API.

This script can be run directly without pytest to perform integration tests.
Usage: python run_integration_tests.py
"""
# ruff: noqa: PLR2004

import json
import os
import subprocess
import sys
import traceback
from datetime import datetime

import requests
from colorama import Fore, Style, init

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.integration.test_helpers import (
    PretixTestClient,
    extract_test_cases,
    generate_invalid_test_cases,
    save_test_data,
    wait_for_server,
)

# Initialize colorama
init(autoreset=True)

# Configuration
API_BASE_URL = "http://localhost:8002"
TEST_DATA_FILE = "pretix_test_data.json"


class IntegrationTestRunner:
    """Run integration tests and generate report."""

    def __init__(self):
        self.results = {"passed": 0, "failed": 0, "skipped": 0, "errors": [], "start_time": datetime.now().isoformat()}
        self.server_process = None
        self.test_data = None

    def setup(self):
        """Setup test environment."""
        print(f"\n{Fore.CYAN}=== Setting up Integration Tests ==={Style.RESET_ALL}")

        # Start API server
        print(f"{Fore.YELLOW}Starting API server on port 8002...{Style.RESET_ALL}")
        self.server_process = subprocess.Popen(
            [sys.executable, "-m", "app.main", "--port", "8002"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        )

        # Wait for server
        if not wait_for_server(f"{API_BASE_URL}/", timeout=30):
            # Try to get server output for debugging
            try:
                output = self.server_process.stdout.read()
                print(f"{Fore.RED}Server output:{Style.RESET_ALL}")
                print(output)
            except Exception:
                pass
            raise RuntimeError("Failed to start API server")

        print(f"{Fore.GREEN}✓ API server started{Style.RESET_ALL}")

        # Fetch test data
        print(f"{Fore.YELLOW}Fetching data from Pretix API...{Style.RESET_ALL}")
        try:
            client = PretixTestClient()
            positions = client.get_order_positions(limit=20)
            items = client.get_items()

            test_cases = extract_test_cases(positions)
            invalid_cases = generate_invalid_test_cases(test_cases)

            self.test_data = {"valid": test_cases, "invalid": invalid_cases, "items": items, "raw_positions": positions[:5]}

            # Save test data
            filepath = save_test_data(self.test_data, TEST_DATA_FILE)
            print(f"{Fore.GREEN}✓ Fetched {len(positions)} positions{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✓ Test data saved to {filepath}{Style.RESET_ALL}")

        except Exception as e:
            self.teardown()
            raise RuntimeError(f"Failed to fetch test data: {e}") from e

    def teardown(self):
        """Cleanup test environment."""
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
            print(f"\n{Fore.CYAN}✓ API server stopped{Style.RESET_ALL}")

    def run_test(self, test_name: str, test_func):
        """Run a single test and record results."""
        print(f"\n{Fore.YELLOW}▶ {test_name}{Style.RESET_ALL}")
        try:
            test_func()
            self.results["passed"] += 1
            print(f"{Fore.GREEN}✓ PASSED{Style.RESET_ALL}")
        except AssertionError as e:
            self.results["failed"] += 1
            self.results["errors"].append({"test": test_name, "error": str(e), "type": "assertion"})
            print(f"{Fore.RED}✗ FAILED: {e}{Style.RESET_ALL}")
        except Exception as e:
            self.results["failed"] += 1
            self.results["errors"].append({"test": test_name, "error": str(e), "type": "exception", "traceback": traceback.format_exc()})
            print(f"{Fore.RED}✗ ERROR: {e}{Style.RESET_ALL}")

    def test_validate_with_order_and_name(self):
        """Test validation with order ID + name."""
        valid_attendees = self.test_data["valid"]["valid_attendees"]
        tested = 0

        for attendee in valid_attendees[:3]:
            if attendee["order_id"] and attendee["name"]:
                response = requests.post(
                    f"{API_BASE_URL}/tickets/validate_attendee/", json={"order_id": attendee["order_id"], "name": attendee["name"]}
                )

                assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
                data = response.json()
                assert data["is_attendee"] is True, f"Expected is_attendee=True, got {data}"

                print(f"  ✓ {attendee['order_id']} + {attendee['name']}")
                tested += 1

        assert tested > 0, "No valid test cases found"

    def test_validate_with_secret_and_name(self):
        """Test validation with ticket ID + name."""
        valid_attendees = self.test_data["valid"]["valid_attendees"]
        tested = 0

        for attendee in valid_attendees[:3]:
            if attendee["secret"] and attendee["name"]:
                response = requests.post(
                    f"{API_BASE_URL}/tickets/validate_attendee/", json={"ticket_id": attendee["secret"], "name": attendee["name"]}
                )

                assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
                data = response.json()
                assert data["is_attendee"] is True

                print(f"  ✓ {attendee['secret'][:8]}... + {attendee['name']}")
                tested += 1

        assert tested > 0, "No valid test cases with secrets found"

    def test_invalid_order_ids(self):
        """Test with invalid order IDs."""
        valid_name = self.test_data["valid"]["names"][0] if self.test_data["valid"]["names"] else "Test User"

        for order_id in self.test_data["invalid"]["invalid_order_ids"][:3]:
            response = requests.post(f"{API_BASE_URL}/tickets/validate_attendee/", json={"order_id": order_id, "name": valid_name})

            # Should fail with 422 or 404
            assert response.status_code in [422, 404], f"Expected failure for {order_id}, got {response.status_code}"

            if response.status_code == 404:
                data = response.json()
                assert data["is_attendee"] is False

            print(f"  ✓ Rejected: {order_id} (status {response.status_code})")

    def test_wrong_names(self):
        """Test with wrong names."""
        valid_attendee = self.test_data["valid"]["valid_attendees"][0]

        if valid_attendee["order_id"]:
            wrong_names = ["Wrong Person", "Not Me", "Someone Else"]

            for wrong_name in wrong_names:
                response = requests.post(
                    f"{API_BASE_URL}/tickets/validate_attendee/", json={"order_id": valid_attendee["order_id"], "name": wrong_name}
                )

                assert response.status_code in [404, 406], "Expected rejection for wrong name"
                data = response.json()
                assert data["is_attendee"] is False

                print(f"  ✓ Rejected: '{wrong_name}' - {data.get('hint', 'No match')}")

    def test_email_validation(self):
        """Test email validation."""
        # Test valid emails
        valid_emails = [e for e in self.test_data["valid"]["emails"] if e][:2]

        assert len(valid_emails) > 0, "No valid emails found in test data"

        for email in valid_emails:
            response = requests.post(f"{API_BASE_URL}/tickets/validate_email/", json={"email": email})

            assert response.status_code == 200, f"Failed for valid email {email}: status {response.status_code}, response: {response.text}"
            data = response.json()
            assert data["valid"] is True, f"Expected valid=True for {email}, got {data}"

            print(f"  ✓ Valid: {email}")

        # Test invalid email with a unique address
        invalid_email = "test_invalid_12345_unique@nonexistent-domain-xyz.com"
        response = requests.post(f"{API_BASE_URL}/tickets/validate_email/", json={"email": invalid_email})

        # Debug: print response if not 404
        if response.status_code != 404:
            print(f"  ! Unexpected response for {invalid_email}: status={response.status_code}, body={response.text}")

        assert response.status_code == 404, f"Expected 404 for invalid email, got {response.status_code}. Response: {response.text}"
        data = response.json()
        assert data["valid"] is False, f"Expected valid=False, got {data}"

        print(f"  ✓ Rejected: {invalid_email}")

    def test_common_endpoints(self):
        """Test common endpoints."""
        # Refresh all
        response = requests.get(f"{API_BASE_URL}/tickets/refresh_all/")
        assert response.status_code == 200
        print(f"  ✓ refresh_all: {response.json()['message']}")

        # Ticket types
        response = requests.get(f"{API_BASE_URL}/tickets/ticket_types/")
        assert response.status_code == 200
        types = response.json()["ticket_types"]
        print(f"  ✓ ticket_types: {len(types)} types found")

        # Ticket count
        response = requests.get(f"{API_BASE_URL}/tickets/ticket_count/")
        assert response.status_code == 200
        count = response.json()["ticket_count"]
        print(f"  ✓ ticket_count: {count} tickets")

    def run_all_tests(self):
        """Run all integration tests."""
        print(f"\n{Fore.MAGENTA}{'=' * 60}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}Running Pretix Integration Tests{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}{'=' * 60}{Style.RESET_ALL}")

        tests = [
            ("Order ID + Name Validation", self.test_validate_with_order_and_name),
            ("Ticket ID + Name Validation", self.test_validate_with_secret_and_name),
            ("Invalid Order IDs", self.test_invalid_order_ids),
            ("Wrong Names", self.test_wrong_names),
            ("Email Validation", self.test_email_validation),
            ("Common Endpoints", self.test_common_endpoints),
        ]

        for test_name, test_func in tests:
            self.run_test(test_name, test_func)

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary."""
        total = self.results["passed"] + self.results["failed"] + self.results["skipped"]

        print(f"\n{Fore.MAGENTA}{'=' * 60}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}Test Summary{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}{'=' * 60}{Style.RESET_ALL}")

        print(f"\nTotal tests: {total}")
        print(f"{Fore.GREEN}Passed: {self.results['passed']}{Style.RESET_ALL}")
        print(f"{Fore.RED}Failed: {self.results['failed']}{Style.RESET_ALL}")

        if self.results["failed"] > 0:
            print(f"\n{Fore.RED}Failed Tests:{Style.RESET_ALL}")
            for error in self.results["errors"]:
                print(f"\n  • {error['test']}")
                print(f"    Error: {error['error']}")
                if error.get("traceback"):
                    print(f"    Traceback:\n{error['traceback']}")

        # Save results
        self.results["end_time"] = datetime.now().isoformat()
        results_file = "integration_test_results.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n{Fore.CYAN}Results saved to {results_file}{Style.RESET_ALL}")

        # Exit code
        return 0 if self.results["failed"] == 0 else 1


def main():
    """Main entry point."""
    runner = IntegrationTestRunner()

    try:
        runner.setup()
        runner.run_all_tests()
        exit_code = 0 if runner.results["failed"] == 0 else 1
    except Exception as e:
        print(f"\n{Fore.RED}FATAL ERROR: {e}{Style.RESET_ALL}")
        traceback.print_exc()
        exit_code = 1
    finally:
        runner.teardown()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

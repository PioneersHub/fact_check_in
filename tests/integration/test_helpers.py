"""Helper functions for integration tests."""

import json
import os
import time

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class PretixTestClient:
    """Client for fetching real data from Pretix API."""

    def __init__(self):
        self.token = os.getenv("PRETIX_TOKEN")
        self.base_url = os.getenv("PRETIX_BASE_URL", "https://pretix.eu/api/v1")
        self.organizer = os.getenv("PRETIX_ORGANIZER_SLUG")
        self.event = os.getenv("PRETIX_EVENT_SLUG")

        if not all([self.token, self.organizer, self.event]):
            raise ValueError("Missing Pretix configuration in .env")

        self.headers = {"Authorization": f"Token {self.token}", "Content-Type": "application/json"}

    def get_order_positions(self, limit: int = 10) -> list[dict]:
        """Fetch real order positions from Pretix."""
        url = f"{self.base_url}/organizers/{self.organizer}/events/{self.event}/orderpositions/"
        params = {"limit": limit, "ordering": "-datetime"}

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        data = response.json()
        return data.get("results", [])

    def get_items(self) -> list[dict]:
        """Fetch all items (ticket types) from Pretix."""
        url = f"{self.base_url}/organizers/{self.organizer}/events/{self.event}/items/"

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        data = response.json()
        return data.get("results", [])


def save_test_data(data: dict, filename: str):
    """Save test data to a JSON file."""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    return filepath


def load_test_data(filename: str) -> dict:
    """Load test data from a JSON file."""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath) as f:
        return json.load(f)


def extract_test_cases(positions: list[dict]) -> dict:
    """Extract test cases from real Pretix data."""
    test_cases = {"valid_attendees": [], "order_ids": set(), "secrets": [], "emails": [], "names": []}

    for pos in positions:
        if pos.get("attendee_name") and pos.get("order"):
            # Extract order code from order URL or code
            order_code = pos["order"].split("/")[-2] if "/" in pos["order"] else pos["order"]

            # Handle item - it might be an ID or object
            item_name = "Unknown"
            item_data = pos.get("item")
            if isinstance(item_data, dict):
                # Item is embedded as object
                name_data = item_data.get("name", {})
                item_name = name_data.get("en", "Unknown") if isinstance(name_data, dict) else str(name_data)
            else:
                # Item is just an ID
                item_name = f"Item ID: {item_data}"

            attendee = {
                "order_id": order_code,
                "secret": pos.get("secret", ""),
                "name": pos.get("attendee_name", ""),
                "email": pos.get("attendee_email", ""),
                "item_name": item_name,
            }

            test_cases["valid_attendees"].append(attendee)
            test_cases["order_ids"].add(order_code)
            test_cases["secrets"].append(pos.get("secret", ""))
            test_cases["emails"].append(pos.get("attendee_email", ""))
            test_cases["names"].append(pos.get("attendee_name", ""))

    # Convert set to list
    test_cases["order_ids"] = list(test_cases["order_ids"])

    # Filter out empty values
    test_cases["secrets"] = [s for s in test_cases["secrets"] if s]
    test_cases["emails"] = [e for e in test_cases["emails"] if e]
    test_cases["names"] = [n for n in test_cases["names"] if n]

    return test_cases


def generate_invalid_test_cases(valid_cases: dict) -> dict:
    """Generate invalid test cases based on valid data."""
    invalid_cases = {
        "invalid_order_ids": [
            "XXXXX",  # Non-existent
            "ABC1O",  # Contains forbidden O and 1
            "AB",  # Too short
            "ABCDEF",  # Too long
            "ABC@#",  # Invalid characters
            "12345",  # Valid format but non-existent
        ],
        "invalid_secrets": [
            "x" * 32,  # Wrong secret
            "tooshort",  # Too short
            "x" * 33,  # Too long
            "abc123!@#$%^&*()abc123!@#$%^&*()",  # Invalid characters
        ],
        "invalid_emails": ["notanemail", "missing@domain", "@nodomain.com", "spaces in@email.com", "definitely.not.registered@example.com"],
        "mismatched_names": [],
    }

    # Generate mismatched names from valid names
    for name in valid_cases.get("names", [])[:3]:
        if name:
            # Completely wrong name
            invalid_cases["mismatched_names"].append(name[::-1])  # Reversed
            # Partial match (should fail if not close enough)
            invalid_cases["mismatched_names"].append(name.split()[0] if " " in name else name + "son")

    return invalid_cases


def wait_for_server(url: str, timeout: int = 30) -> bool:
    """Wait for the server to be ready."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url)
            if response.status_code in [200, 404]:  # Any response means server is up
                return True
        except requests.exceptions.ConnectionError:
            pass
        except Exception as e:
            print(f"Error checking server: {e}")
        time.sleep(1)
    return False

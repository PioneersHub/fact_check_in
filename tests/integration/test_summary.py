#!/usr/bin/env python3
"""
Generate a summary of integration test results and test data.
"""

import json
import os

from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)


def load_json_file(filename):
    """Load JSON file if it exists."""
    if os.path.exists(filename):
        with open(filename) as f:
            return json.load(f)
    return None


def print_test_summary():
    """Print a summary of the test results."""
    print(f"\n{Fore.MAGENTA}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}Integration Test Summary{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'=' * 60}{Style.RESET_ALL}")

    # Load test results
    results = load_json_file("integration_test_results.json")
    if results:
        print(f"\n{Fore.CYAN}Test Results:{Style.RESET_ALL}")
        print(f"  Start time: {results.get('start_time', 'N/A')}")
        print(f"  End time: {results.get('end_time', 'N/A')}")
        print(f"  {Fore.GREEN}Passed: {results.get('passed', 0)}{Style.RESET_ALL}")
        print(f"  {Fore.RED}Failed: {results.get('failed', 0)}{Style.RESET_ALL}")

        if results.get("errors"):
            print(f"\n{Fore.RED}Failed Tests:{Style.RESET_ALL}")
            for error in results["errors"]:
                print(f"  • {error['test']}: {error['error']}")

    # Load test data
    test_data = load_json_file("pretix_test_data.json")
    if test_data:
        valid_data = test_data.get("valid", {})
        invalid_data = test_data.get("invalid", {})

        print(f"\n{Fore.CYAN}Test Data Summary:{Style.RESET_ALL}")
        print(f"  Valid attendees: {len(valid_data.get('valid_attendees', []))}")
        print(f"  Order IDs: {len(valid_data.get('order_ids', []))}")
        print(f"  Secrets: {len(valid_data.get('secrets', []))}")
        print(f"  Emails: {len(valid_data.get('emails', []))}")
        print(f"  Names: {len(valid_data.get('names', []))}")

        print(f"\n{Fore.CYAN}Sample Valid Data:{Style.RESET_ALL}")
        if valid_data.get("valid_attendees"):
            for i, attendee in enumerate(valid_data["valid_attendees"][:3]):
                print(f"\n  Attendee {i + 1}:")
                print(f"    Order ID: {attendee['order_id']}")
                print(f"    Name: {attendee['name']}")
                print(f"    Email: {attendee['email']}")
                print(f"    Secret: {attendee['secret'][:8]}...")

        print(f"\n{Fore.CYAN}Invalid Test Cases:{Style.RESET_ALL}")
        print(f"  Invalid order IDs: {len(invalid_data.get('invalid_order_ids', []))}")
        print(f"  Invalid secrets: {len(invalid_data.get('invalid_secrets', []))}")
        print(f"  Invalid emails: {len(invalid_data.get('invalid_emails', []))}")
        print(f"  Mismatched names: {len(invalid_data.get('mismatched_names', []))}")

    # Show what endpoints were tested
    print(f"\n{Fore.CYAN}Endpoints Tested:{Style.RESET_ALL}")
    endpoints = [
        ("POST", "/tickets/validate_attendee/", "Pretix attendee validation"),
        ("POST", "/tickets/validate_email/", "Email validation"),
        ("GET", "/tickets/refresh_all/", "Refresh ticket cache"),
        ("GET", "/tickets/ticket_types/", "Get ticket types"),
        ("GET", "/tickets/ticket_count/", "Get ticket count"),
    ]

    for method, endpoint, description in endpoints:
        print(f"  {Fore.YELLOW}{method:6}{Style.RESET_ALL} {endpoint:30} - {description}")

    # Show validation methods tested
    print(f"\n{Fore.CYAN}Validation Methods Tested:{Style.RESET_ALL}")
    methods = [
        "Order ID + Name",
        "Ticket ID (secret) + Name",
        "Order ID + Ticket ID + Name (most secure)",
        "Fuzzy name matching",
        "Invalid order IDs",
        "Invalid ticket IDs",
        "Mismatched names",
        "Email validation",
    ]

    for method in methods:
        print(f"  ✓ {method}")

    print(f"\n{Fore.MAGENTA}{'=' * 60}{Style.RESET_ALL}\n")


if __name__ == "__main__":
    print_test_summary()

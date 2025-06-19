#!/usr/bin/env python3
"""
Debug script to test email search behavior directly.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import interface
from app.pretix import pretix_api

# Test the search function directly
test_email = "test_invalid_12345_unique@nonexistent-domain-xyz.com"
print(f"Testing search for: {test_email}")

# Initialize API
pretix_api.get_all_ticket_offers()
pretix_api.get_all_tickets()

# Search
results = pretix_api.search(test_email)
print(f"Search results: {len(results)} found")
for i, result in enumerate(results):
    print(f"\nResult {i + 1}:")
    print(f"  Reference: {result.get('reference')}")
    print(f"  Email: {result.get('email')}")
    print(f"  Name: {result.get('name')}")
    print(f"  Release ID: {result.get('release_id')}")

# Check interface.valid_ticket_ids
print(f"\nValid ticket IDs: {interface.valid_ticket_ids}")

# Filter results by valid ticket IDs
filtered = [x for x in results if x.get("release_id") in interface.valid_ticket_ids]
print(f"\nFiltered results (valid tickets only): {len(filtered)}")

if filtered:
    print("This explains why the email validation returns valid=True!")

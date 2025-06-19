# Pretix Integration Tests

This directory contains integration tests for the Pretix ticketing backend implementation.

## Overview

The integration tests verify the complete flow of the Pretix API implementation by:
1. Fetching real data from the Pretix API
2. Testing all validation endpoints with real and invalid data
3. Verifying the expected behavior matches our implementation

## Test Coverage

### Endpoints Tested

- **POST /tickets/validate_attendee/** - Pretix attendee validation
  - Order ID + Name
  - Ticket ID (secret) + Name
  - Order ID + Ticket ID + Name (most secure)
- **POST /tickets/validate_email/** - Email validation
- **GET /tickets/refresh_all/** - Refresh ticket cache
- **GET /tickets/ticket_types/** - Get ticket types
- **GET /tickets/ticket_count/** - Get ticket count

### Validation Methods

1. **Positive Tests**:
   - Valid order ID + correct name
   - Valid ticket ID + correct name
   - Valid order ID + ticket ID + correct name
   - Fuzzy name matching (case variations, extra spaces)
   - Valid email addresses

2. **Negative Tests**:
   - Invalid order IDs (wrong format, contains O/1, non-existent)
   - Invalid ticket IDs (wrong length, non-existent)
   - Correct order ID but wrong name
   - Correct ticket ID but wrong name
   - Mismatched order ID and ticket ID
   - Non-existent email addresses

## Running the Tests

### Prerequisites

1. Ensure you have the Pretix API credentials in your `.env` file:
   ```env
   PRETIX_TOKEN="your-token"
   PRETIX_BASE_URL="https://pretix.eu/api/v1"
   PRETIX_ORGANIZER_SLUG="your-organizer"
   PRETIX_EVENT_SLUG="your-event"
   TICKETING_BACKEND=pretix
   ```

2. Install required dependencies:
   ```bash
   pip install requests colorama pytest
   ```

### Running Tests

1. **Run the standalone integration test script**:
   ```bash
   python tests/integration/run_integration_tests.py
   ```

2. **Run with pytest**:
   ```bash
   pytest tests/integration/test_pretix_live.py -v
   ```

3. **View test summary**:
   ```bash
   python tests/integration/test_summary.py
   ```

### Debug Tools

- `debug_email_search.py` - Debug email search behavior directly
- `test_helpers.py` - Utility functions for fetching and processing test data

## Test Data

The tests automatically fetch real data from Pretix and save it to:
- `pretix_test_data.json` - Contains valid and invalid test cases
- `integration_test_results.json` - Test execution results

## Key Implementation Details

### Order ID Format
- 5 alphanumeric characters (A-Z, 0-9)
- Excludes letters 'O' and digit '1' to avoid confusion
- Examples: XZKHM, NNJEP, YM3TE

### Ticket ID (Secret) Format
- 32 character alphanumeric string
- Lowercase
- Example: m526nf8vseamchcw2jn26zxc6cfxg8gp

### Name Matching
- Uses fuzzy matching with configurable thresholds
- Case-insensitive
- Handles extra spaces and minor variations
- Exact match threshold: 0.95
- Close match threshold: 0.80

### Attribute Mapping
The tests verify that ticket attributes are correctly mapped based on:
- Item name patterns (e.g., "Remote" → is_remote=True)
- Category mappings (configured in base.yml)
- Default attributes for unmapped items

## Common Issues

1. **Email validation returning unexpected results**:
   - The Pretix API may return all results when no match is found
   - Fixed by adding client-side filtering to verify actual matches

2. **Order codes containing O or 1**:
   - These are invalid per Pretix documentation
   - Validation rejects these with error 422

3. **Test data changes**:
   - Tests fetch live data, so results may vary
   - Use specific test accounts if consistent data is needed

## Contributing

When adding new tests:
1. Follow the existing pattern in `test_pretix_live.py`
2. Add both positive and negative test cases
3. Update this README with new test coverage
4. Ensure all tests pass before committing
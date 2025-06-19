# Pretix Fake Data Reference

This document explains the structure of the Pretix fake test data files and provides links to the official Pretix API documentation that was used as reference.

## Files Overview

- `fake_all_sales_pretix.json` - Simulates Pretix order positions (tickets)
- `fake_all_releases_pretix.json` - Simulates Pretix items/products with categories

## Pretix API Documentation References

### Order Positions (fake_all_sales_pretix.json)

**API Documentation**: https://docs.pretix.eu/en/latest/api/resources/orders.html

This file simulates order positions from the Pretix API. Key aspects:

- **Reference Format**: `ORDER123-1` (Order code + position ID)
  - Order codes use A-Z and 0-9 (excluding O and 1)
  - Example: Order "ORDER123" with position 1 becomes "ORDER123-1"

- **Order Status Values**:
  - `n` - pending
  - `p` - paid (mapped to "complete" in our system)
  - `e` - expired
  - `c` - canceled

- **Structure Example**:
```json
{
  "ORDER123-1": {
    "reference": "ORDER123-1",
    "email": "angel.hill@example.net",
    "name": "Angel Hill",
    "release_id": 101,
    "state": "complete",
    "created_at": "2025-02-03T20:54:50.205574+02:00",
    "updated_at": "2025-02-03T21:31:50.205574+02:00",
    "assigned": true,
    "_pretix_data": {
      "order": "ORDER123",
      "positionid": 1,
      "secret": "kzjf832jf",
      "item": 101,
      "variation": null
    }
  }
}
```

### Items/Products (fake_all_releases_pretix.json)

**API Documentation**: https://docs.pretix.eu/en/latest/api/resources/items.html

This file simulates items (products/tickets) from the Pretix API. Key aspects:

- **Multi-lingual Names**: Pretix supports language codes (we use English)
- **Categories**: Items can belong to categories for organization
- **Admission**: Whether the item grants event admission
- **Variations**: Products can have variations (not used in our fake data)

### Categories

**API Documentation**: https://docs.pretix.eu/en/latest/api/resources/categories.html

Categories are included within the releases file. Key aspects:

- **Structure**:
```json
{
  "category_id": 1004,
  "category": {
    "id": 1004,
    "name": "Speaker",
    "internal_name": "speaker"
  }
}
```

- **Purpose**: Categories help organize items and in our system, map to attendee attributes

## Data Mapping

### From Pretix to Our System

1. **Order Positions → Sales/Tickets**
   - `order + positionid` → `reference`
   - `attendee_email` → `email`
   - `attendee_name` → `name`
   - `item` → `release_id`
   - `order__status` → `state` (p=complete, n=pending)

2. **Items → Releases**
   - `id` → `id`
   - `name` → `title`
   - `category` → `category_id` and `category` object
   - Derived → `activities` (based on name patterns)
   - Derived → `_attributes` (from category mapping)

## Test Data Scenarios

The fake data includes various ticket types to test different scenarios:

1. **Regular Tickets** (IDs 101-105)
   - Conference Pass
   - Remote Conference Pass
   - Business Ticket

2. **Special Access Tickets** (IDs 106-108)
   - Speaker Pass (category: Speaker)
   - Volunteer Pass (category: Volunteer)
   - Sponsor Pass (category: Sponsor)

3. **Day Passes** (ID 109)
   - Monday Day Pass (tests day-specific logic)

4. **VIP Access** (ID 110)
   - VIP Guest Pass (category: VIP)

5. **Edge Cases**
   - Unassigned ticket (ORDERPQR-1) - no email/name
   - Pending status ticket

## Usage in Tests

When writing tests with Pretix fake data:

1. Set environment variable: `TICKETING_BACKEND=pretix`
2. The Interface class will automatically load Pretix fake data
3. Categories will be extracted and available in `interface.categories`
4. All data follows the actual Pretix API structure

## Validation

The test file `tests/test_pretix.py` validates:
- Correct reference format (ORDER-style)
- Presence of _pretix_data fields
- Category structure
- Attribute mappings
- Activities derived from names/categories
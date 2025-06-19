# Pretix Fake Data Reference

This document explains the structure of the Pretix fake test data files and provides links to the official Pretix API documentation that was used as reference.

## Important Note

The fake data files represent **TRANSFORMED** data after processing by our system, not raw Pretix API responses. This matches what the Interface class stores after calling the Pretix API.

## Files Overview

- `fake_all_sales_pretix.json` - Simulates **transformed** Pretix order positions
- `fake_all_releases_pretix.json` - Simulates **transformed** Pretix items with categories

## Pretix API Documentation References

### Order Positions (fake_all_sales_pretix.json)

**API Documentation**: https://docs.pretix.eu/en/latest/api/resources/orders.html

#### Raw Pretix API Structure (for reference):
```json
{
  "id": 23442,
  "order": "ABC12",
  "positionid": 1,
  "item": 1345,
  "attendee_name": "Peter",
  "attendee_email": "peter@example.com",
  "secret": "z3fsn8jyufm5kpk768q69gkbyr5f4h6w",
  "created": "2021-04-06T13:44:22.000Z",
  "modified": "2021-04-06T13:44:22.000Z"
}
```

#### Our Transformed Structure:
```json
{
  "ABC12-1": {
    "reference": "ABC12-1",
    "email": "peter@example.com",
    "name": "Peter",
    "release_id": 1345,
    "state": "complete",
    "created_at": "2021-04-06T13:44:22.000Z",
    "updated_at": "2021-04-06T13:44:22.000Z",
    "assigned": true,
    "_pretix_data": {
      "order": "ABC12",
      "positionid": 1,
      "secret": "z3fsn8jyufm5kpk768q69gkbyr5f4h6w",
      "item": 1345,
      "variation": null
    }
  }
}
```

#### Key Transformations:
- `order + positionid` → `reference` (e.g., "ABC12-1")
- `attendee_email` → `email`
- `attendee_name` → `name`
- `item` → `release_id`
- Order status `"p"` → `state: "complete"`
- `created` → `created_at`
- `modified` → `updated_at`
- `secret` preserved (32-character alphanumeric string)

#### Order Code Format:
- Order codes use A-Z and 0-9 (excluding "O" and "1")
- ✅ Valid examples in our fake data: "ABC23", "DEF456", "GHJ789", "PQRSTU"
- All fake order codes now comply with Pretix rules

#### Order Status:
- When querying orderpositions, use `order__status` as a filter parameter
- The order itself has a `status` field
- Values: `n` (pending), `p` (paid), `e` (expired), `c` (canceled)
- Our code correctly uses `pos.get("order__status")` when the position includes expanded order data

### Items/Products (fake_all_releases_pretix.json)

**API Documentation**: https://docs.pretix.eu/en/latest/api/resources/items.html

#### Raw Pretix API Structure (for reference):
```json
{
  "id": 1345,
  "name": {"en": "Standard ticket"},
  "category": 1001,
  "admission": true,
  "default_price": "23.00",
  "active": true,
  "variations": []
}
```

#### Our Transformed Structure:
```json
{
  "STANDARD TICKET": {
    "id": 1345,
    "title": "Standard ticket",
    "category_id": 1001,
    "category": {
      "id": 1001,
      "name": "Regular Tickets",
      "internal_name": "regular"
    },
    "activities": ["on_site", "online_access"],
    "_attributes": {
      "is_remote": false,
      "is_onsite": true,
      "online_access": true,
      "is_speaker": false,
      "is_sponsor": false,
      "is_volunteer": false,
      "is_organizer": false,
      "is_guest": false
    }
  }
}
```

#### Key Transformations:
- `name["en"]` → `title` (extracted from multi-lingual name)
- `category` → `category_id` + full category object
- Derived → `activities` (based on name patterns and category)
- Derived → `_attributes` (from category mapping and name patterns)
- Key is uppercase title for compatibility with existing system

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
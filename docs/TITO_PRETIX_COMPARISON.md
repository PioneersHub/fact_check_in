# Tito vs Pretix: Feature Comparison for Fact Check-in

This document compares how Tito and Pretix handle ticketing features in the context of the Fact Check-in system.

## Architectural Differences

### Backend Implementation
- **Tito**: Direct activity-based model with native support for multi-activity tickets
- **Pretix**: Category and product-based model requiring attribute mapping
- **API Design**: Tito uses simple JSON; Pretix uses paginated REST with rich metadata

### Data Loading
- **Tito**: Single API call loads all tickets
- **Pretix**: Paginated requests, may require multiple calls for large events
- **Performance**: Both cache data on startup (~30 seconds)

## Core Concept Differences

### Activities (Tito) vs Product Names (Pretix)

**Tito**: Uses "activities" - a built-in feature where tickets can have multiple activities assigned
```
Ticket: "Conference Pass"
Activities: ["on_site", "online_access", "workshop_access"]
```

**Pretix**: No activities concept - we infer properties from product names
```
Product: "Conference Pass - In-Person with Workshop Access"
→ System interprets: on_site + online_access + workshop features
```

## Data Structure Mapping

| Feature | Tito | Pretix |
|---------|------|--------|
| Unique ID | Reference (e.g., "ABCD-1") | Order-Position (e.g., "ORDER123-1") |
| Ticket Type | Release | Item/Product |
| Attendee Info | Part of ticket sale | Part of order position |
| Access Control | Via activities | Via product name parsing |
| State | Ticket state | Order status |

## Activity to Product Name Mapping

### Basic Access Types

| Tito Activities | Pretix Product Name Must Include | Result |
|----------------|----------------------------------|--------|
| `["remote_sale", "online_access"]` | "online" OR "remote" OR "virtual" | Remote attendee with online access |
| `["on_site", "online_access"]` | "in-person" OR "on-site" OR "venue" | Physical attendee with online access |
| `["on_site"]` only | "in-person" WITHOUT online keywords | Physical attendance only |

### Day-Specific Access

| Tito Activities | Pretix Product Name | Example |
|----------------|---------------------|---------|
| `["on_site", "seat-person-monday"]` | Must include "day pass" AND "monday" | "Monday Day Pass" |
| `["on_site", "seat-person-tuesday"]` | Must include "day pass" AND "tuesday" | "Tuesday Day Pass" |

### Special Attendee Types

Both systems use the same name-based detection:

| Attendee Type | Detection Method | Works in Both? |
|--------------|------------------|----------------|
| Speaker | "speaker" in ticket/product name | ✅ Yes |
| Sponsor | "sponsor" in ticket/product name | ✅ Yes |
| Organizer | "organiser" in ticket/product name | ✅ Yes |
| Volunteer | "volunteer" in ticket/product name | ✅ Yes |
| Day Pass Sponsor | "day pass" in ticket/product name | ✅ Yes |

## Configuration Differences

### Tito Configuration
```yaml
# In base.yml
include_activities:
  - conference-remote_sale  
  - pydata-remote_sale
  - on_site
  - online_access
  - seat-person-monday
  # ... more activities
```

### Pretix Configuration
No activity configuration needed - all logic is in product names.

## API Differences

### Fetching Tickets

**Tito API**:
```
GET /registrations
Returns: tickets with embedded activities
```

**Pretix API**:
```
GET /orderpositions/
Returns: order positions linked to items (products)
```

### Data Transform Example

**Tito Data**:
```json
{
  "reference": "ABCD-1",
  "release_title": "Conference Pass",
  "activities": ["on_site", "online_access"]
}
```

**Pretix Data** (transformed):
```json
{
  "reference": "ORDER123-1",
  "item_name": "Conference Pass - In-Person",
  "activities": ["on_site", "online_access"]  // Inferred from name
}
```

## Migration Strategy

When moving from Tito to Pretix or supporting both:

### 1. Map Your Activities to Product Names

Create a mapping table:
```
Tito Release + Activities → Pretix Product Name
"Conference Pass" + ["on_site"] → "Conference Pass - In-Person"
"Conference Pass" + ["remote_sale"] → "Conference Pass - Online Only"
"Workshop Ticket" + ["on_site", "workshop"] → "Workshop Ticket - On-Site Access"
```

### 2. Naming Convention

Establish clear patterns:
- **Remote tickets**: Always include "Online" or "Remote"
- **Physical tickets**: Always include "In-Person" or "On-Site"
- **Day passes**: Format as "[Day] Day Pass"
- **Special roles**: Include role in name (Speaker Pass, Sponsor Pass)

### 3. Testing Checklist

- [ ] All attendee types detected correctly
- [ ] Access rights (remote/onsite) properly assigned
- [ ] Day passes grant correct daily access
- [ ] Special attendee flags (speaker, sponsor) work
- [ ] Name validation matches expected behavior

## Advantages and Limitations

### Tito Advantages
- Explicit activity system
- More flexible access control
- Activities can be added/removed without changing ticket names

### Pretix Advantages  
- Simpler setup (no activity configuration)
- Product names are self-documenting
- Works well with naming conventions

### Limitations in Pretix
- Cannot have complex activity combinations without verbose names
- Changing access requires renaming products
- Must follow naming conventions strictly

## Category Mapping (Pretix Advanced Feature)

### Overview
Pretix categories provide a more robust way to map attendee attributes without relying on product names.

### Configuration Example
```yaml
pretix_mapping:
  categories:
    by_id:
      999001:  # Speaker category ID
        is_speaker: true
      999002:  # Sponsor category ID  
        is_sponsor: true
    by_name:  # Fallback if IDs change
      "speaker":
        is_speaker: true
      "sponsor":
        is_sponsor: true
```

### Benefits
- Cleaner product names (no need for role keywords)
- Easier to manage multiple attributes
- More maintainable than name-based detection

## Performance Comparison

| Metric | Tito | Pretix |
|--------|------|--------|
| Initial Load Time | ~20-30s | ~20-40s (depends on pagination) |
| API Calls on Startup | 2 (tickets + releases) | 3+ (items + categories + positions) |
| Memory Usage | Lower | Higher (rich metadata) |
| Validation Speed | Same | Same (cached) |

## Recommendations

1. **For Simple Events**: Pretix's name-based system is sufficient
2. **For Complex Access Control**: Tito's activities provide more flexibility  
3. **For Large Events**: Consider Pretix's category system over name-based
4. **For Migration**: Start with clear product naming in Pretix that mirrors your Tito activities
5. **For Dual Support**: Run both systems with `TICKETING_BACKEND` configuration

## Quick Reference: Setting Up Equivalent Tickets

### Example 1: Basic Conference

**Tito Setup**:
- Release: "Conference Ticket"
- Activities: ["on_site", "online_access"]

**Pretix Equivalent**:
- Product: "Conference Ticket - In-Person"

### Example 2: Online Only Event

**Tito Setup**:
- Release: "Streaming Pass"  
- Activities: ["remote_sale", "online_access"]

**Pretix Equivalent**:
- Product: "Streaming Pass - Online Only"

### Example 3: Multi-Day with Daily Access

**Tito Setup**:
- Release: "Tuesday Only"
- Activities: ["on_site", "seat-person-tuesday", "online_access"]

**Pretix Equivalent**:
- Product: "Tuesday Day Pass - On-Site"

### Example 4: VIP Access

**Tito Setup**:
- Release: "VIP Pass"
- Activities: ["on_site", "online_access", "vip_lounge", "all_workshops"]

**Pretix Equivalent**:
- Product: "VIP Pass - Full Access In-Person"
- Note: Complex permissions may need additional handling
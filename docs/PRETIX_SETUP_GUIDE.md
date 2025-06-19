# Pretix Setup Guide for Fact Check-in

This guide explains how to configure your Pretix event to work seamlessly with the Fact Check-in system, which was originally designed for Tito's activity-based tickets.

## Key Concept: Activity Mapping

Since Pretix doesn't have "activities" like Tito, the Fact Check-in system determines ticket properties based on **product/item names**. This means careful naming of your Pretix products is essential.

## Product Naming Conventions

### 1. Access Type Indicators

Include these keywords in your product names to specify access type:

#### Remote/Online Only Tickets
Include any of: `online`, `remote`, `virtual`, `streaming`
- Examples:
  - "Conference Pass - Online Only"
  - "Remote Attendee Ticket"
  - "Virtual Access Pass"
  - "Streaming Ticket"

#### In-Person Tickets
Include any of: `in-person`, `on-site`, `physical`, `venue`
- Examples:
  - "Conference Pass - In-Person"
  - "On-Site Attendee Ticket"
  - "Venue Access Pass"
  - "Physical Attendance Ticket"

**Note**: In-person tickets automatically include online access in the system.

### 2. Attendee Type Indicators

Include these keywords to automatically categorize attendees:

| Keyword in Name | Attendee Type | Example Product Names |
|----------------|---------------|----------------------|
| `speaker` | Speaker | "Speaker Pass", "Conference Speaker Ticket" |
| `organiser` | Organizer | "Organiser Pass", "Event Organiser Ticket" |
| `sponsor` | Sponsor | "Sponsor Pass", "Gold Sponsor Ticket" |
| `volunteer` | Volunteer | "Volunteer Pass", "Helper Volunteer Ticket" |
| `day pass` | Sponsor* | "Monday Day Pass", "Day Pass - Tuesday" |

*Day passes are categorized as sponsors for special handling.

### 3. Day Pass Configuration

For day-specific access, include both "day pass" and the day name:
- "Monday Day Pass" → Grants Monday access
- "Tuesday Day Pass" → Grants Tuesday access
- "Wednesday Day Pass" → Grants Wednesday access

The system will automatically assign the appropriate day-specific activities.

## Complete Product Name Examples

Here are recommended product names that will work perfectly with the system:

### Standard Tickets
- "Early Bird Ticket - In-Person"
- "Regular Ticket - Online Only"
- "Student Ticket - On-Site"
- "Business Ticket - Remote Access"

### Special Access
- "Speaker Pass - In-Person"
- "Sponsor Pass - Gold Level"
- "Organiser Pass - Full Access"
- "Volunteer Pass - Weekend"
- "Media Pass - On-Site"

### Day Passes
- "Monday Day Pass - In-Person"
- "Tuesday Day Pass - On-Site"
- "Wednesday Day Pass - Venue Access"

## Configuration in Pretix

### 1. Create Products

In Pretix admin:
1. Go to Products → Add Product
2. Use the naming conventions above
3. Set appropriate prices and quotas

### 2. Optional: Use Categories

While not required, you can organize products into categories for better management:
- "Attendee Tickets"
- "Speaker & VIP"
- "Day Passes"
- "Online Only"

### 3. Attendee Information

Ensure you collect:
- **Name** (required) - Used for fuzzy matching during check-in
- **Email** (required) - Used for validation

### 4. Order States

The system considers orders as valid when:
- Order status is "Paid" (`p` in API)
- Other statuses are treated as "pending"

## API Setup

### 1. Create API Token

In Pretix:
1. Go to Settings → API tokens
2. Create a new token with these permissions:
   - "Can view orders"
   - "Can view event settings"

### 2. Configure Fact Check-in

Set these environment variables:
```bash
TICKETING_BACKEND=pretix
PRETIX_TOKEN="your_api_token"
PRETIX_BASE_URL="https://pretix.eu/api/v1"  # or your instance URL
PRETIX_ORGANIZER_SLUG="your_organizer"
PRETIX_EVENT_SLUG="your_event"
```

## Testing Your Setup

### 1. Verify Product Names

After creating products, test that they're properly categorized:
```bash
# Start the app with Pretix backend
TICKETING_BACKEND=pretix uvicorn app.main:app

# Check ticket types endpoint
curl http://localhost:8080/tickets/ticket_types/
```

### 2. Test Validation

Create a test order and validate:
```bash
# Validate by reference and name
curl -X POST http://localhost:8080/tickets/validate_name/ \
  -H "Content-Type: application/json" \
  -d '{"ticket_id": "ORDER123-1", "name": "John Doe"}'
```

### 3. Verify Access Rights

Check the response includes correct flags:
- `is_speaker`, `is_sponsor`, `is_organizer`, `is_volunteer`
- `is_remote`, `is_onsite`, `online_access`

## Migration from Tito

If migrating from Tito, map your activities to product names:

| Tito Activity | Pretix Product Name Should Include |
|--------------|-----------------------------------|
| `remote_sale` | "online", "remote", or "virtual" |
| `on_site` | "in-person", "on-site", or "venue" |
| `online_access` | (Automatic for most tickets) |
| `seat-person-monday` | "monday day pass" |

## Troubleshooting

### Issue: Tickets not showing correct access type
**Solution**: Check product names include the required keywords (case-insensitive)

### Issue: Day passes not working
**Solution**: Ensure name includes both "day pass" and the day name

### Issue: Attendee type not detected
**Solution**: Include type keyword ("speaker", "sponsor", etc.) in product name

### Issue: No tickets loading
**Solution**: Verify API token permissions and credentials

## Best Practices

1. **Consistent Naming**: Use a clear pattern for all products
2. **Test Early**: Create test orders before your event
3. **Document Mappings**: Keep a record of how Pretix products map to attendee types
4. **Use English**: The system expects English keywords in product names
5. **Include Access Type**: Always specify if a ticket is online-only or in-person

## Example Event Setup

For a typical conference:

```
Products:
├── Regular Tickets
│   ├── "Early Bird - In-Person Access"
│   ├── "Regular - In-Person Access"
│   ├── "Student - In-Person Access"
│   └── "Regular - Online Only"
├── Special Access
│   ├── "Speaker Pass"
│   ├── "Sponsor Pass - Gold"
│   ├── "Sponsor Pass - Silver"
│   └── "Organiser Pass"
├── Day Passes
│   ├── "Monday Day Pass"
│   ├── "Tuesday Day Pass"
│   └── "Wednesday Day Pass"
└── Other
    └── "Volunteer Pass"
```

This structure ensures all attendees are properly categorized and have the correct access rights in the check-in system.
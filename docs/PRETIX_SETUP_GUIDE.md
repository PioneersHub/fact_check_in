# Pretix Setup Guide

Configure your Pretix event to work with Fact Check-in by following product naming conventions.

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

## Pretix Configuration

1. **Create Products** with naming conventions above
2. **Collect Attendee Info**: Name and Email (required)
3. **Order States**: Only "Paid" orders are valid

## API Setup

1. **Create API Token** in Pretix Settings → API tokens
   - Required permissions: "Can view orders", "Can view event settings"

2. **Configure** `.env` file:
```bash
TICKETING_BACKEND=pretix
PRETIX_TOKEN="your_api_token"
PRETIX_BASE_URL="https://pretix.eu/api/v1"
PRETIX_ORGANIZER_SLUG="your_organizer"
PRETIX_EVENT_SLUG="your_event"
```

## Quick Test

```bash
# Start with Pretix backend
TICKETING_BACKEND=pretix uvicorn app.main:app

# Test validation
curl -X POST http://localhost:8080/tickets/validate_name/ \
  -H "Content-Type: application/json" \
  -d '{"ticket_id": "ORDER123-1", "name": "John Doe"}'
```

## Troubleshooting

- **Wrong access type?** Check product name includes keywords (online/in-person)
- **Day pass not working?** Include both "day pass" and day name
- **Type not detected?** Add role keyword to product name
- **No tickets loading?** Verify API token and permissions

## Example Product Structure

```
Regular Tickets/
├── Early Bird - In-Person
├── Regular - Online Only
Special Access/
├── Speaker Pass
├── Sponsor Pass - Gold
Day Passes/
├── Monday Day Pass
├── Tuesday Day Pass
```
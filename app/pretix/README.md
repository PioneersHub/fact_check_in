# Pretix Integration

This module provides integration with the Pretix ticketing system as an alternative to Tito.

## Configuration

To use Pretix instead of Tito, you need to:

1. Set the ticketing backend in your configuration:
   - Set `TICKETING_BACKEND: pretix` in `app/config/base.yml` or
   - Set environment variable `TICKETING_BACKEND=pretix`

2. Configure Pretix API credentials in your `.env` file:
   ```bash
   PRETIX_TOKEN="your_pretix_api_token"
   PRETIX_BASE_URL="https://pretix.eu/api/v1"  # or your self-hosted instance
   PRETIX_ORGANIZER_SLUG="your_organizer_slug"
   PRETIX_EVENT_SLUG="your_event_slug"
   ```

## How It Works

The Pretix adapter maps Pretix concepts to the existing Tito-based system:

### Data Mapping

| Tito Concept | Pretix Concept | Notes |
|--------------|----------------|-------|
| Ticket | Order Position | Each attendee in an order |
| Reference (ABCD-1) | Order-Position (ORDER123-1) | Constructed from order code + position |
| Release | Item/Product | Ticket types |
| Activities | (Simulated from item names) | Pretix doesn't have activities |

### Activity Simulation

Since Pretix doesn't have an "activities" concept like Tito, the adapter determines activities based on item names:

- Items with "online", "remote", "virtual", "streaming" → `remote_sale`, `online_access`
- Items with "in-person", "on-site", "physical", "venue" → `on_site`, `online_access`
- Items with "day pass" → `on_site` + day-specific activities
- Default → `on_site`, `online_access`

### Attendee Type Detection

Attendee types are still determined by ticket/item names (same as Tito):
- "speaker" in name → `is_speaker`
- "organiser" in name → `is_organizer`
- "sponsor" in name → `is_sponsor`
- "day pass" in name → `is_sponsor` (special handling)
- "volunteer" in name → `is_volunteer`

## API Endpoints Used

The Pretix adapter uses these API endpoints:
- `GET /organizers/{org}/events/{event}/orderpositions/` - Get attendee data
- `GET /organizers/{org}/events/{event}/items/` - Get ticket types

## Testing

To test the Pretix integration:

1. Set up test credentials in `.env`
2. Set `TICKETING_BACKEND=pretix`
3. Run the application
4. Test the validation endpoints

## Differences from Tito

1. **Reference Format**: Pretix uses "ORDER123-1" format instead of "ABCD-1"
2. **No Activities**: Activity-based filtering is simulated from item names
3. **Search**: Pretix supports searching by partial email/name matches
4. **Multi-language**: Item names can be in multiple languages (defaults to English)
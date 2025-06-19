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

3. Configure attribute mappings in `app/config/base.yml`:
   ```yaml
   pretix_mapping:
     categories:
       by_id:
         123456:  # Your Speaker category ID
           is_speaker: true
       by_name:
         "speaker":
           is_speaker: true
   ```

## How It Works

The Pretix adapter maps Pretix concepts to the existing Tito-based system:

### Data Mapping

| Tito Concept | Pretix Concept | Notes |
|--------------|----------------|-------|
| Ticket | Order Position | Each attendee in an order |
| Reference (ABCD-1) | Order-Position (ORDER123-1) | Constructed from order code + position |
| Release | Item/Product | Ticket types |
| Activities | (Simulated from attributes) | Pretix doesn't have activities |

### Attribute Mapping System

The new mapping system provides flexible ways to assign attendee attributes:

1. **Category-Based Mapping** (Recommended):
   - Map by Category ID (highest priority)
   - Map by Category Name
   - Configure in `app/config/base.yml`

2. **Product Name Detection** (Fallback):
   - Detects keywords in product names
   - Automatic for common patterns

3. **Access Type Detection**:
   - "online", "remote", "virtual" → Remote access
   - "in-person", "on-site", "venue" → On-site access
   - Default: On-site with online access

### Startup Validation

The system validates attribute mappings on startup:
- Shows which attributes have no tickets mapped
- Provides coverage statistics
- Suggests improvements

Example output:
```
⚠️  The following attributes have NO tickets mapped to them:
  ❌ is_speaker
     → Suggestion: Create a 'Speaker' category in Pretix
```

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
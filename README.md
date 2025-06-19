# Fact Check-in

> Validate if the attendee is registered for the conference by ticket code, name and email

## Features

1. Validate if the attendee is registered for the conference by ticket code and name
2. Validate if the attendee is registered by email
3. Provide information about the registration type (attendee, speaker, sponsor, organizer, etc.)

## Use Cases

1. Automatically add the attendee to the conference Discord assigning roles based on the registration type
2. Allow access to a video-streaming platform for conference talks


The REST-API returns the following information:

Important: run with ONE worker only!
```
uvicorn main:app --port 8080 --host "0.0.0.0" 
```

It takes about 30 sec to launch, data is loaded and processed from the ticketing system (Tito or Pretix).

## Set-Up

### Using Tito (Default)

Add a `.env` file with the following content:

```text
TITO_TOKEN="your_secret_token"
ACCOUNT_SLUG="account_slug_from_tito"
EVENT_SLUG="event_slug_from_tito"
```

### Using Pretix

To use Pretix instead of Tito:

1. Set the ticketing backend in `app/config/base.yml`:
   ```yaml
   TICKETING_BACKEND: pretix
   ```

2. Add Pretix credentials to your `.env` file:
   ```text
   PRETIX_TOKEN="your_pretix_api_token"
   PRETIX_BASE_URL="https://pretix.eu/api/v1"  # or your self-hosted instance
   PRETIX_ORGANIZER_SLUG="your_organizer_slug"
   PRETIX_EVENT_SLUG="your_event_slug"
   ```

See [app/pretix/README.md](app/pretix/README.md) for technical details on the Pretix integration.

For setting up your Pretix event to work with this system, see:
- [Pretix Setup Guide](docs/PRETIX_SETUP_GUIDE.md) - How to configure products in Pretix
- [Tito vs Pretix Comparison](docs/TITO_PRETIX_COMPARISON.md) - Detailed feature comparison

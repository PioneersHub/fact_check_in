# Fact Check-in

REST API to validate conference attendees using Tito or Pretix ticketing systems.

## Quick Start

### 1. Install Dependencies
```bash
# Requires Python 3.12+
uv pip install -e .
```

### 2. Configure Ticketing System

**Option A: Tito (Default)**
```bash
# Create .env file
TITO_TOKEN="your_secret_token"
ACCOUNT_SLUG="account_slug_from_tito"
EVENT_SLUG="event_slug_from_tito"
```

**Option B: Pretix**
```bash
# Create .env file
PRETIX_TOKEN="your_pretix_api_token"
PRETIX_BASE_URL="https://pretix.eu/api/v1"
PRETIX_ORGANIZER_SLUG="your_organizer_slug"
PRETIX_EVENT_SLUG="your_event_slug"

# Set backend (environment variable takes precedence over config file)
TICKETING_BACKEND=pretix
```

### 3. Run the Application
```bash
# IMPORTANT: Use single worker only!
uvicorn app.main:app --port 8080 --host "0.0.0.0"
```

**Note**: Startup takes ~30 seconds while loading ticket data.

## Features

- Validate attendees by ticket code + name (with fuzzy matching)
- Validate attendees by email
- Identify attendee types (speaker, sponsor, organizer, volunteer)
- Distinguish access levels (on-site, remote, online)

## API Endpoints

- `POST /tickets/validate_name/` - Validate by ticket ID and name
- `POST /tickets/validate_email/` - Validate by email
- `GET /tickets/refresh_all/` - Force reload ticket data
- `GET /healthcheck/alive` - Health check

## Development

```bash
# Install with dev dependencies
uv pip install -e .

# Set up pre-commit hooks
pre-commit install --hook-type pre-commit --hook-type pre-push

# Run tests
pytest

# Run linting/formatting
ruff check . --fix
ruff format .
```

## Documentation

- [CLAUDE.md](CLAUDE.md) - Development guide for Claude Code
- [Pretix Setup Guide](docs/PRETIX_SETUP_GUIDE.md) - Configure Pretix products
- [Tito vs Pretix Comparison](docs/TITO_PRETIX_COMPARISON.md) - Feature comparison

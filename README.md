# Fact Check-in

REST API to validate conference attendees using multiple ticketing systems through a modular backend architecture.

## Supported Ticketing Systems

- **Tito** - Default backend with native activity support
- **Pretix** - Full integration with category-based attribute mapping

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

**API Documentation**: Once running, visit:
- Interactive API docs: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## Features

- **Modular Backend Architecture**: Easily switch between ticketing systems or add new ones
- **Dynamic Configuration**: Backend selection via environment variables or config files
- **Smart Validation**: 
  - Validate attendees by ticket code + name (with fuzzy matching)
  - Validate attendees by email
  - Configurable name matching thresholds
- **Flexible Attribute Mapping**: 
  - Tito: Native activity support
  - Pretix: Category and product name-based mapping
- **Special Attendee Types**: Automatic detection of speakers, sponsors, volunteers, organizers
- **Access Level Detection**: Distinguish between on-site, remote, and online attendees
- **Day Pass Support**: Handle day-specific access (Monday, Tuesday, etc.)

## Backend Architecture

The application uses a modular backend system that allows seamless switching between different ticketing platforms:

- **Abstract Interface**: `TicketingBackend` base class defines the contract
- **Dynamic Loading**: Backends are loaded at runtime based on configuration
- **Consistent API**: Same REST endpoints work with any backend
- **Easy Extension**: Add new backends by implementing the interface

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

- [Developer Guide](DEVELOPER.md) - Development setup and guidelines
- [Pretix Setup Guide](docs/PRETIX_SETUP_GUIDE.md) - Configure Pretix products
- [Tito vs Pretix Comparison](docs/TITO_PRETIX_COMPARISON.md) - Feature comparison
- [API Documentation](http://localhost:8080/docs) - Interactive API docs (when running)

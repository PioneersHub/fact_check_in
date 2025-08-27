# Fact Check-in

REST API to validate conference attendees using multiple ticketing systems through a modular backend architecture.

## Supported Ticketing Systems

- **Tito** - Default backend with native activity support
- **Pretix** - Full integration with category-based attribute mapping

## Quick Start

#### Build-In `attributes`

The following attributes are built-in and default toi `False`:

- is_onsite
- is_remote
- online_access
- is_speaker
- is_sponsor
- is_volunteer
- is_organizer
- is_guest

### 0. Ticketing System Setup: in Pretix

It's important to follow a base structure when setting up the tickets in pretix already.

Roles can bes assigned via:

#### 1. Ticket categories  ("Product categories" in Pretix)

The category defines on-site and remote access baseline (e.g. attributes: is_remote, is_onsite, online_access)

#### 2. Tickets including variations ("Products" in Pretix)

This will update the attributes set in 1.

A usual use case is to add is_speaker for speaker tickets for example.

#### 3. Order ID ('ABCDE-1') ("Orders" in Pretix, note one order can have multiple items 'ABCDE-1, 'ABCDE-2',…)

This will update the attributes set in 1. and 2.

This is mostly used to handle multiple roles if a person is:

- organizer_and_speaker: The person is an organizer and gives a talk.
- organizer_and_sponsor: The person is an organizer and the employer is also sponsor.
- speaker_and_sponsor: The person is a speaker and the employer is also sponsor.
- speaker_add_keynote: The person is a keynote speaker.
- add_speaker: The person is a speaker but has a non-speaker ticket for some reason.

This is a **direct** assignment for that one ticket for that **one** person

#### Access rights Assignment

Access rights are assigned in the following order:

1. Ticket category
2. Ticket ID
3. Order ID

Any step might change attributes. The best practice is to only add access, i,e. setting attributes to True. A mix of adding and removing
access will be confusing.


#### **Pitfalls**

##### Use case: Social Event

You grant all ticket holders access to remote attendance `online_access: True`.
But there are also social event tickets available for a +1, social event tickets does not include `online_access`

- put event tickets in own category, e.,g. Social Event

```yaml
pretix_mapping:
  categories:
    by_id:
      999: # ID of social event category
        online_access: False
    # OR exclude one or multiple ticket IDs
    by_ticket_id:
      8888: # ID of social event ticket
        online_access: False
```

##### ⚠️: Change of Category

The category can very easily be changed in the Pretix backend.
Other people might do that to:

- get a nicer look on the stats
- improve the ticket shop order.

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

### 3. Configure Event Mapping (Pretix only)

Edit `event_config.yml` to map your event's ticket categories and special roles:

```yaml
# Set backend
TICKETING_BACKEND: pretix

pretix_mapping:
  categories:
    by_id:
      227668: # Your category ID
        is_onsite: true
        online_access: true

    by_ticket_id:
      819314: # Speaker ticket ID
        is_speaker: true

  # Special multi-role assignments
  speaker_and_sponsor:
    - "C3UAP-1"  # Ticket code
```

### 4. Run the Application

**Option A: Direct Run**

```bash
# IMPORTANT: Use single worker only!
uvicorn app.main:app --port 8080 --host "0.0.0.0"
```

**Option B: Docker**

```bash
# Set environment variables in .env file or export them
export TITO_TOKEN="your_token"
export ACCOUNT_SLUG="your_account"
export EVENT_SLUG="your_event"

# Build and run
docker-compose up --build

# Or run pre-built image
docker-compose up
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

## Agentic API

This project was partially updated with Claude CLI. Instructions for Claude are in [CLAUDE.md](CLAUDE.md)

## Documentation

- [Developer Guide](DEVELOPER.md) - Development setup and guidelines
- [API Documentation](http://localhost:8080/docs) - Interactive API docs (when running)


# Other

There are issues of the library that created the social cards on macOS, the cairo svg library is required: `brew install cairo`.  
Even if installed cairo might not be found. Fixes:

- `export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`
- Add a symlink in project root: `ln -s /opt/homebrew/opt/cairo/lib/libcairo.2.dylib`
# Development Guidelines

This file provides guidelines for AI assistants and developers working with this codebase.

## Project Overview

Fact Check-in is a FastAPI-based REST API service that validates conference attendees using multiple ticketing systems (Tito, Pretix) through a modular backend architecture. The service performs ticket validation using ticket codes and fuzzy name matching, and categorizes attendees by type (speaker, sponsor, organizer, volunteer, etc.).

## Development Commands

### Environment Setup
```bash
# Install dependencies using uv package manager
uv pip install -e .

# Create .env file with required credentials:

# For Tito (default):
# TITO_TOKEN="your_secret_token"
# ACCOUNT_SLUG="account_slug_from_tito"
# EVENT_SLUG="event_slug_from_tito"

# For Pretix:
# TICKETING_BACKEND=pretix
# PRETIX_TOKEN="your_api_token"
# PRETIX_BASE_URL="https://pretix.eu/api/v1"
# PRETIX_ORGANIZER_SLUG="your_organizer"
# PRETIX_EVENT_SLUG="your_event"
```

### Running the Application
```bash
# Run locally (IMPORTANT: use ONE worker only to avoid data sync issues)
uvicorn app.main:app --port 8080 --host "0.0.0.0"
# OR with reload for development
uvicorn app.main:app --reload

# Run with Docker
docker-compose up
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_name_tickets.py

# Run smoke tests only
pytest -m smoke_test
```

### Code Quality
```bash
# Ruff is configured for linting and formatting
# Pre-commit hooks are installed for both commit and push
# They will automatically run ruff check and format

# To install/update pre-commit hooks:
pre-commit install --hook-type pre-commit --hook-type pre-push

# Run linting manually
ruff check . --fix

# Run formatting manually
ruff format .

# Run all pre-commit hooks manually
pre-commit run --all-files
```

### Version Management
```bash
# Check current version first
bump2version minor --dry-run

# Bump version (follows semantic versioning)
bump2version minor  # e.g., 0.5.1 → 0.6.0
bump2version patch  # e.g., 0.5.1 → 0.5.2

# Set development version after release
bump2version release --new-version 0.6.0dev1
```

## Architecture Overview

### Key Components

1. **API Layer** (`app/routers/tickets.py`)
   - Main validation endpoint: `POST /tickets/validate_name/`
   - Performs fuzzy name matching (95% = pass, 80-95% = close match but fail)
   - Special handling for day pass tickets (app/routers/tickets.py:128-129)
   - Categorizes attendees by type based on ticket attributes

2. **Data Layer** (`app/tito/`)
   - `TicketDataInterfaceBase` manages ticket cache
   - Loads data from Tito API on startup (~30 seconds)
   - Supports refresh via `/tickets/refresh_all/` endpoint

3. **Configuration** (`app/config/`)
   - Uses OmegaConf for configuration management
   - Environment variables loaded from `.env` file
   - Test mode available via `FAKE_CHECK_IN_TEST_MODE=1`

4. **Models** (`app/models/`)
   - Pydantic models for request/response validation
   - Strict type checking at runtime

### Testing Strategy

The project uses comprehensive testing with:
- **pytest** with async support for FastAPI testing
- **Hypothesis** for property-based testing with random inputs
- **Fake data** loaded from JSON files in `tests/fake_data/`
- **Fixtures** in `conftest.py` that support both live service and test client testing

### Important Patterns

1. **Single Worker Requirement**: The application must run with only one worker to maintain data consistency
2. **Fuzzy Name Matching**: Uses SequenceMatcher for flexible name validation
3. **Attendee Categorization**: Logic in `app/routers/tickets.py` determines attendee types
4. **Environment-based Configuration**: Different behavior for test vs production modes
5. **Docker Deployment**: Containerized deployment with uv package manager
6. **Pretix Category Mapping**: Flexible attribute mapping system for Pretix tickets via categories or product names

## Common Development Tasks

When implementing new features:
1. Check existing patterns in `app/routers/` for API endpoints
2. Add Pydantic models in `app/models/` for new data structures
3. Write tests following patterns in `tests/` directory
4. Use structured logging with `structlog` for debugging
5. Ensure code passes Ruff linting before committing

When debugging:
- The application logs extensively with structlog
- Test mode can be enabled with `FAKE_CHECK_IN_TEST_MODE=1`
- Individual tests can be run with pytest for faster iteration

## Pretix Integration

The application supports Pretix as an alternative to Tito. Key features:

### Category-Based Attribute Mapping
Configure in `app/config/base.yml`:
```yaml
pretix_mapping:
  categories:
    by_id:
      123456:  # Pretix category ID
        is_speaker: true
    by_name:
      "speaker":  # Match category names
        is_speaker: true
```

### Startup Validation
- Automatically validates attribute coverage on startup
- Shows unmapped attributes with suggestions
- Helps identify configuration issues early

### Mapping Priority
1. Category ID mapping (highest priority)
2. Category name mapping
3. Product name patterns (fallback)
4. Default attributes

When working with Pretix:
- Check validation output on startup for coverage gaps
- Use categories for explicit attribute control
- Product names still determine access type (remote/onsite)

## Versioning

This project uses semantic versioning (SemVer) with bumpversion for automatic version management.

### Version Format
`MAJOR.MINOR.PATCH` (e.g., 0.7.0)

### When to Bump Versions
- **MAJOR**: Breaking API changes, major refactoring
- **MINOR**: New features, significant enhancements (like Pretix integration)
- **PATCH**: Bug fixes, minor improvements

### Creating a New Version
```bash
# For bug fixes
bumpversion patch

# For new features
bumpversion minor

# For breaking changes
bumpversion major
```

This automatically:
- Updates version in pyproject.toml, app/__init__.py, and .bumpversion.cfg
- Creates a commit with message "Bump version: X.Y.Z → X.Y.Z"
- Creates a git tag (vX.Y.Z)

### Push Tags
```bash
git push origin --tags
```
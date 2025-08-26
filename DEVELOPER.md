# Developer Guide

## Setup

### 1. Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager

### 2. Install Development Environment
```bash
# Clone and enter repository
git clone <repo-url>
cd fact_check_in

# Install dependencies
uv pip install -e .

# Set up pre-commit hooks
pre-commit install --hook-type pre-commit --hook-type pre-push
```

### 3. Configure Environment
```bash
# Copy example env file
cp .env.example .env  # or .env.pretix.example for Pretix

# Edit .env with your credentials
```

## Running Locally

```bash
# Start server (MUST use single worker!)
uvicorn app.main:app --reload --port 8080

# Or using Python module
python -m app.main
```

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_name_tickets.py

# Run backend-specific tests
TICKETING_BACKEND=tito pytest tests/test_name_tickets.py
TICKETING_BACKEND=pretix pytest tests/test_pretix.py

# Run smoke tests only
pytest -m smoke_test

# Run with coverage
pytest --cov=app
```

### Backend-Specific Testing
- Tito tests use `tests/test_data/fake_all_sales.json`
- Pretix tests use `tests/test_data/fake_all_sales_pretix.json`
- Tests automatically load appropriate fake data based on backend

## Backend Development

### Adding a New Ticketing Backend

1. Create a new directory: `app/your_backend/`

2. Implement the backend interface in `app/your_backend/backend.py`:
```python
from app.ticketing.backend import TicketingBackend

class YourBackend(TicketingBackend):
    def get_all_tickets(self):
        # Implementation
    
    def get_all_ticket_offers(self):
        # Implementation
    
    def search_reference(self, reference: str):
        # Implementation
    
    def search(self, search_for: str):
        # Implementation
    
    def get_router(self):
        from .router import router
        return router
```

3. Create router in `app/your_backend/router.py` with backend-specific endpoints

4. Add backend name to `app/ticketing/backend.py` in `get_backend()` function

5. Create test data in `tests/test_data/fake_all_sales_yourbackend.json`

6. Update `app/middleware/interface.py` to load backend-specific test data

### Backend Selection
- Set via environment variable: `TICKETING_BACKEND=your_backend`
- Or in `app/config/base.yml`: `TICKETING_BACKEND: your_backend`
- Environment variables take precedence over config file

## Code Quality

Pre-commit hooks automatically run on every commit. To run manually:

```bash
# Run all checks
pre-commit run --all-files

# Run linting with fixes
ruff check . --fix

# Run formatter
ruff format .
```

## Deployment

### Release Process
1. Ensure clean repository (all changes committed, tests pass)
2. Bump version to release
3. Deploy
4. Bump version to development state

## Versioning Schema
The versioning schema is `{major}.{minor}.{patch}[{release}{build}]` where the
latter part (release and build) is optional.
Release takes the following values:
- _null_
- _dev_ (to indicate a actively developed version)
- _a_ (alpha)
- _b_ (beta)
- _rc_ (release candidate)
- _post_ (post release hotfixes)

### Bump version identifier
It is recommended to do `--dry-run` prior to your actual run.
```bash
# increase version identifier
bump2version [major/minor/patch/release/build]  # --verbose --dry-run

# e.g.
bump2version minor  # e.g. 0.5.1 --> 0.6.0
bump2version minor --new-version 0.7.0  # e.g. 0.5.1 --> 0.7.0
```
After a successful release, the version identifier should be bumped to the `dev` state to indicate
that master/main is under development. The exact version does not matter to much, e.g. work that was
initially considered a patch could be bumped as a minor release upon release.
```bash
bump2version release --new-version 0.6.0dev1  # e.g. 0.5.1 --> 0.6.0dev1
```

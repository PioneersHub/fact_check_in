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

# Run smoke tests only
pytest -m smoke_test

# Run with coverage
pytest --cov=app
```

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

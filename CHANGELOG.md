# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Backward-incompatible changes:
none
### Deprecations:
none
### Changes:
none

## [1.0.0] - 2025-06-19

### Major Features
- **Modular Backend Architecture**: Complete separation of Tito and Pretix ticketing systems with pluggable backend design
- **Dynamic Router Loading**: Backend-specific API routers are loaded at runtime based on configuration
- **Full Pretix Integration**: Comprehensive support for Pretix API including categories, items, and order positions
- **Enhanced Configuration**: Support for environment variable overrides and backend-specific settings

### Added
- Abstract `TicketingBackend` interface for implementing new ticketing systems
- Separate backend implementations in `app/tito/` and `app/pretix/` directories
- Dynamic backend selection via `TICKETING_BACKEND` environment variable
- Pretix category-based attribute mapping for speakers, sponsors, volunteers, etc.
- Configurable name matching thresholds (exact: 0.95, close: 0.8)
- Day pass ticket support with automatic activity assignment
- Comprehensive fake test data for both Tito and Pretix backends
- Backend-specific API documentation and setup guides
- Improved test isolation with pytest fixtures for backend switching
- Structured logging with better error handling

### Changed
- Moved backend-specific logic out of common modules into dedicated implementations
- Router loading now happens dynamically based on selected backend
- Test infrastructure updated to support backend-specific test suites
- Configuration system now uses environment variable precedence over config files
- API endpoints remain consistent across backends for compatibility

### Fixed
- Test isolation issues when switching between backends
- Backend caching problems in test environments
- Singleton pattern issues with Interface class
- Environment variable configuration precedence

### Backward-incompatible changes
- Direct imports from `app.routers.tickets` no longer work (use dynamic loading)
- Backend configuration must be set before application startup
- Test files must explicitly set backend for proper operation

## [0.7.0] - 2025-06-17
- Add Pretix backend support
- Move log files to dedicated logs directory
- Add versioning guidelines

## [0.6.2] - 2025-05-15
- Fix pre-commit configuration

## [0.6.1] - 2025-05-15
- Fix pre-commit hooks

## [0.6.0] - 2025-05-15
- Add ruff linting and formatting
- Move name matching thresholds to configuration

## 0.5.0 - 2025-02-22
- Cleanup of redundant code and documentation
- Switch to uv, removed conda, requirements
- Switch to mkdocs, removed sphinx

## 0.1.0 - 2023-03-29
- Initial Setup

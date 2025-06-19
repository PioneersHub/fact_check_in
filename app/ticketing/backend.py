"""
Ticketing backend abstraction layer.

This module provides a unified interface for different ticketing systems (Tito, Pretix).
"""

from app import log
from app.config import CONFIG


class TicketingBackend:
    """Abstract base class for ticketing backends."""

    def get_all_tickets(self):
        """Load all tickets/order positions."""
        raise NotImplementedError

    def get_all_ticket_offers(self):
        """Load all ticket types/items."""
        raise NotImplementedError

    def search_reference(self, reference: str):
        """Search for a ticket by reference/ID."""
        raise NotImplementedError

    def search(self, search_for: str):
        """Search for tickets by email or name."""
        raise NotImplementedError

    def get_router(self):
        """Return the backend-specific router."""
        raise NotImplementedError


def get_backend_name() -> str:
    """Get the configured backend name."""
    import os

    backend_name = os.environ.get("TICKETING_BACKEND") or CONFIG.get("TICKETING_BACKEND", "tito")
    return backend_name.lower()


def get_backend() -> TicketingBackend:
    """Dynamically load the configured ticketing backend."""
    backend_name = get_backend_name()

    try:
        if backend_name == "tito":
            log.info("Using Tito ticketing backend")
            from app.tito.backend import TitoBackend

            return TitoBackend()
        elif backend_name == "pretix":
            log.info("Using Pretix ticketing backend")
            from app.pretix.backend import PretixBackend

            return PretixBackend()
        else:
            raise ValueError(f"Unknown ticketing backend: {backend_name}")
    except ImportError as e:
        raise ImportError(f"Backend '{backend_name}' not found. Module may have been removed.") from e


# Global backend instance
_backend = None


def get_ticketing_backend() -> TicketingBackend:
    """Get or create the global ticketing backend instance."""
    global _backend  # noqa: PLW0603
    if _backend is None:
        _backend = get_backend()
    return _backend

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


class TitoBackend(TicketingBackend):
    """Tito ticketing system backend."""

    def __init__(self):
        from app.tito import tito_api

        self.api = tito_api

    def get_all_tickets(self):
        return self.api.get_all_tickets()

    def get_all_ticket_offers(self):
        return self.api.get_all_ticket_offers()

    def search_reference(self, reference: str):
        return self.api.search_reference(reference)

    def search(self, search_for: str):
        return self.api.search(search_for)


class PretixBackend(TicketingBackend):
    """Pretix ticketing system backend."""

    def __init__(self):
        from app.pretix import pretix_api

        self.api = pretix_api

    def get_all_tickets(self):
        return self.api.get_all_tickets()

    def get_all_ticket_offers(self):
        return self.api.get_all_ticket_offers()

    def search_reference(self, reference: str):
        return self.api.search_reference(reference)

    def search(self, search_for: str):
        return self.api.search(search_for)


def get_backend() -> TicketingBackend:
    """Get the configured ticketing backend."""
    import os

    # Check environment variable first, then fall back to config
    backend_name = os.environ.get("TICKETING_BACKEND") or CONFIG.get("TICKETING_BACKEND", "tito")
    backend_name = backend_name.lower()

    if backend_name == "tito":
        log.info("Using Tito ticketing backend")
        return TitoBackend()
    elif backend_name == "pretix":
        log.info("Using Pretix ticketing backend")
        return PretixBackend()
    else:
        raise ValueError(f"Unknown ticketing backend: {backend_name}")


# Global backend instance
_backend = None


def get_ticketing_backend() -> TicketingBackend:
    """Get or create the global ticketing backend instance."""
    global _backend  # noqa: PLW0603
    if _backend is None:
        _backend = get_backend()
    return _backend

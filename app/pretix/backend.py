"""Pretix backend implementation."""

from app.ticketing.backend import TicketingBackend

from . import pretix_api
from .router import router


class PretixBackend(TicketingBackend):
    """Pretix ticketing system backend."""

    def __init__(self):
        self.api = pretix_api

    def get_all_tickets(self):
        return self.api.get_all_tickets()

    def get_all_ticket_offers(self):
        return self.api.get_all_ticket_offers()

    def search_reference(self, reference: str):
        return self.api.search_reference(reference)

    def search(self, search_for: str):
        return self.api.search(search_for)

    def get_router(self):
        """Return the Pretix-specific router."""
        return router

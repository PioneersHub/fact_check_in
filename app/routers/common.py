"""Common routes shared by all ticketing backends."""

from cachetools import TTLCache, cached
from fastapi import APIRouter

from app import in_dummy_mode, interface, reset_interface
from app.models.base import TicketCount, TicketTypes
from app.ticketing.backend import get_ticketing_backend

router = APIRouter(prefix="/tickets", tags=["Common"])

# Create a cache with maxsize=128 and ttl=300 seconds
cache = TTLCache(maxsize=128, ttl=300)


@router.get("/refresh_all/")
@cached(cache=TTLCache(maxsize=1024, ttl=300))
def refresh_all():
    """
    Service method to force a reload of all ticket data from the ticketing system
    """
    if in_dummy_mode:
        reset_interface(in_dummy_mode)
        return
    backend = get_ticketing_backend()
    backend.get_all_ticket_offers()
    backend.get_all_tickets()
    backend_name = backend.__class__.__name__.replace("Backend", "")
    return {"message": f"The ticket cache was refreshed successfully from {backend_name}."}


@router.get("/ticket_types/", response_model=TicketTypes)
async def get_ticket_types():
    return {"ticket_types": list(interface.all_releases.values())}


@router.get("/ticket_count/", response_model=TicketCount)
async def get_ticket_count():
    return {"ticket_count": len(interface.all_sales)}

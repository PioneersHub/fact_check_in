"""Common routes shared by all ticketing backends."""

from fastapi import APIRouter, Response
from starlette import status

from app import in_dummy_mode, interface, log, reset_interface
from app.models.base import Email, TicketCount, TicketTypes, Truthy
from app.ticketing.backend import get_ticketing_backend

router = APIRouter(prefix="/tickets", tags=["Common"])


@router.get("/refresh_all/")
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


@router.post("/validate_email/", response_model=Truthy)
async def search_email(email: Email, response: Response):
    """
    Live-search for a participant by email.
    """
    req = email.model_dump()
    log.debug(email)
    log.debug(f"searching for email: {req['email']}")
    backend = get_ticketing_backend()
    found = backend.search(req["email"])
    found = [x for x in found if x.get("release_id") in interface.valid_ticket_ids]
    log.debug(f"found: {len(found)}")
    if not found:
        log.info(f"email not found: {req['email']}")
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"valid": False}
    return {"valid": True}

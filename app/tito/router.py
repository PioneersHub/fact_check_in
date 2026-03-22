"""Tito-specific routes."""

from fastapi import APIRouter, Response
from starlette import status

from app import interface, log
from app.config import CONFIG
from app.models.base import Email, Truthy
from app.ticketing.backend import get_ticketing_backend
from app.ticketing.utils import fuzzy_match_name

from .backend import TitoBackend
from .models import TitoAttendee, TitoIsAnAttendee

router = APIRouter(prefix="/tickets", tags=["Tito Validation"])


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


@router.post("/validate_name/", response_model=TitoIsAnAttendee)
async def validate_tito_attendee(attendee: TitoAttendee, response: Response):  # noqa: PLR0912, PLR0915
    """
    Validate a Tito attendee by ticket id and name with fuzzy matching.
    """
    res = attendee.model_dump()
    backend = TitoBackend()

    # ticket_id and name are validated by TitoAttendee field validators, but they
    # have Optional types for schema flexibility; guard against missing values here.
    if not attendee.ticket_id or not attendee.name:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        res["is_attendee"] = False
        res["hint"] = "ticket_id and name are required"
        return res

    ticket_id: str = attendee.ticket_id
    name: str = attendee.name

    # Try to find ticket in cache first
    try:
        ticket = interface.all_sales[ticket_id.upper()]
        log.debug(f"ticket found in cache: {ticket_id}")
    except KeyError:
        log.debug(f"ticket not found in cache: {ticket_id}")
        log.debug(f"trying live search: {ticket_id}")
        try:
            ticket = backend.search_reference(ticket_id)[0]  # type: ignore[index]
            log.debug(f"ticket found via API: {ticket_id}")
        except IndexError, TypeError:
            log.debug(f"attendees loaded: {len(interface.all_sales)}")
            response.status_code = status.HTTP_404_NOT_FOUND
            res["is_attendee"] = False
            res["hint"] = "invalid ticket id"
            return res

    # Get release information
    try:
        ticket["release_title"] = interface.release_id_map[ticket["release_id"]]["title"]
    except KeyError:
        log.error(f"release not found: {ticket['release_id']}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return res

    # Check if ticket type is valid
    if ticket["release_id"] not in interface.valid_ticket_ids:
        response.status_code = status.HTTP_406_NOT_ACCEPTABLE
        res["is_attendee"] = False
        res["hint"] = f"invalid ticket type: {ticket['release_title']}"
        return res

    # Fuzzy name matching
    match_result = fuzzy_match_name(
        ticket.get("name", ""),
        name,
        CONFIG.name_matching.exact_match_threshold,
        CONFIG.name_matching.close_match_threshold,
    )

    if match_result["is_match"]:
        res["is_attendee"] = True
        res["hint"] = match_result.get("hint", "")
    elif match_result["is_close"]:
        res["is_attendee"] = False
        res["hint"] = f"Supplied name {name} is close but not close enough."
    else:
        res["is_attendee"] = False
        res["hint"] = f"We couldn't find {name}, check spelling."

    # Set attendee attributes
    if res["is_attendee"]:
        # Legacy name-based detection for Tito
        release_title_lower = ticket.get("release_title", "").lower()

        if "speaker" in release_title_lower:
            res["is_speaker"] = True
        if "organiser" in release_title_lower:
            res["is_organizer"] = True
            if ticket_id.upper() in CONFIG.organizer_speakers:
                res["is_speaker"] = True
        if "sponsor" in release_title_lower:
            res["is_sponsor"] = True
        if "day pass" in release_title_lower:
            res["is_sponsor"] = True
        if "volunteer" in release_title_lower:
            res["is_volunteer"] = True

        # Activity-based attributes
        if ticket["release_id"] in interface.activity_release_id_map.get("remote_sale", []):
            res["is_remote"] = True
        if ticket["release_id"] in interface.activity_release_id_map.get("on_site", []):
            res["is_onsite"] = True
        if ticket["release_id"] in interface.activity_release_id_map.get("online_access", []):
            res["online_access"] = True

    return res

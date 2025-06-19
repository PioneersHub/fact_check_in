from difflib import SequenceMatcher

from fastapi import APIRouter, Response
from starlette import status

from app import in_dummy_mode, interface, log, reset_interface
from app.config import CONFIG
from app.models.models import Attendee, Email, IsAnAttendee, TicketCount, TicketTypes, Truthy
from app.ticketing.backend import get_ticketing_backend

router = APIRouter(prefix="/tickets", tags=["Attendees"])


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


async def search_ticket(attendee: Attendee, response: Response):
    """
    Live-search for a ticket by ticket ID.
    Do not expose it as an endpoint.
    """
    res = attendee.model_dump()
    backend = get_ticketing_backend()
    found = backend.search_reference(attendee.ticket_id)
    if not found:
        response.status_code = status.HTTP_404_NOT_FOUND
        res["is_attendee"] = False
        res["hint"] = "invalid ticket id"
        return res
    res["is_attendee"] = True
    res["hint"] = ""
    return res


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


@router.post("/validate_name/", response_model=IsAnAttendee)
async def get_ticket_by_id(attendee: Attendee, response: Response):  # noqa: PLR0912, PLR0915
    """
    Validate an attendee by ticket id and name with some fuzzy matching
    """
    res = attendee.model_dump()
    try:
        ticket = interface.all_sales[attendee.ticket_id.upper()]
        print(f"ticket found: {attendee.ticket_id}")
    except KeyError:
        print(f"ticket not found in cache: {attendee.ticket_id}")
        print(f"trying live search: {attendee.ticket_id}")
        try:
            backend = get_ticketing_backend()
            ticket = backend.search_reference(attendee.ticket_id)[0]
            print(f"ticket found: {attendee.ticket_id}")
        except (IndexError, TypeError):
            print(f"attendees loaded: {len(interface.all_sales)}")
            response.status_code = status.HTTP_404_NOT_FOUND
            res["is_attendee"] = False
            res["hint"] = "invalid ticket id"
            return res
    try:
        ticket["release_title"] = interface.release_id_map[ticket["release_id"]]["title"]
    except KeyError:
        print(f"release not found: {ticket['release_id']}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return res

    if ticket["release_id"] not in interface.valid_ticket_ids:
        response.status_code = status.HTTP_406_NOT_ACCEPTABLE
        res["is_attendee"] = False
        res["hint"] = f"invalid ticket type: {ticket['release_title']}"
        return res

    if ticket["name"].strip().upper() == attendee.name.strip().upper():
        res["is_attendee"] = True
    else:
        ratio = SequenceMatcher(None, interface.normalization(ticket["name"]), interface.normalization(attendee.name)).ratio()
        if ratio > CONFIG.name_matching.exact_match_threshold:
            res["is_attendee"] = True
            res["hint"] = ""
        elif ratio > CONFIG.name_matching.close_match_threshold:
            res["is_attendee"] = False
            res["hint"] = f"Supplied name {attendee.name} is close but not close enough."
        else:
            res["is_attendee"] = False
            res["hint"] = f"We couldn't find {attendee.name}, check spelling."

    # Try to get attributes from Pretix mapping first
    release_info = interface.release_id_map.get(ticket["release_id"], {})
    if hasattr(release_info, "_attributes") or "_attributes" in release_info:
        # Use mapped attributes from Pretix
        attributes = release_info.get("_attributes", {})
        res["is_speaker"] = attributes.get("is_speaker", False)
        res["is_organizer"] = attributes.get("is_organizer", False)
        res["is_sponsor"] = attributes.get("is_sponsor", False)
        res["is_volunteer"] = attributes.get("is_volunteer", False)
        res["is_guest"] = attributes.get("is_guest", False)
        res["is_remote"] = attributes.get("is_remote", False)
        res["is_onsite"] = attributes.get("is_onsite", False)
        res["online_access"] = attributes.get("online_access", False)

        # Special case: check organizer speakers list
        if res["is_organizer"] and attendee.ticket_id.upper() in CONFIG.organizer_speakers:
            res["is_speaker"] = True
    else:
        # Fallback to legacy name-based detection for Tito
        if "speaker" in ticket.get("release_title", "").lower():
            res["is_speaker"] = True
        if "organiser" in ticket.get("release_title", "").lower():
            res["is_organizer"] = True
            if attendee.ticket_id.upper() in CONFIG.organizer_speakers:
                res["is_speaker"] = True
        if "sponsor" in ticket.get("release_title", "").lower():
            res["is_sponsor"] = True
        if "day pass" in ticket.get("release_title", "").lower():
            res["is_sponsor"] = True
        if "volunteer" in ticket.get("release_title", "").lower():
            res["is_volunteer"] = True
        if ticket["release_id"] in interface.activity_release_id_map.get("remote_sale", []):
            res["is_remote"] = True
        if ticket["release_id"] in interface.activity_release_id_map.get("on_site", []):
            res["is_onsite"] = True
        if ticket["release_id"] in interface.activity_release_id_map.get("online_access", []):
            res["online_access"] = True
    return res

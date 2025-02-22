from difflib import SequenceMatcher

from fastapi import APIRouter, Response
from starlette import status

from app import in_dummy_mode, interface, log, reset_interface
from app.config import CONFIG
from app.models.models import Attendee, Email, IsAnAttendee, TicketTypes, Truthy
from app.tito.tito_api import get_all_ticket_offers, get_all_tickets, search, search_reference

router = APIRouter(prefix="/tickets", tags=["Attendees"])


@router.get("/refresh_all/")
def refresh_all():
    """
    Service method to force a reload of all ticket data from the ticketing system
    """
    if in_dummy_mode:
        reset_interface(in_dummy_mode)
        return
    get_all_ticket_offers()
    get_all_tickets()
    return {"message": "The ticket cache was refreshed successfully."}


@router.get("/ticket_types/", response_model=TicketTypes)
async def get_ticket_types():
    return {"ticket_types": list(interface.all_releases.values())}


async def search_ticket(attendee: Attendee, response: Response):
    """
    Live-search for a ticket by ticket ID.
    Do not expose it as an endpoint.
    """
    res = attendee.model_dump()
    found = search_reference(attendee.ticket_id)
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
    found = search(req["email"])
    found = [x for x in found if x.get("release_id") in interface.valid_ticket_ids]
    log.debug(f"found: {len(found)}")
    if not found:
        log.info(f"email not found: {req['email']}")
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"valid": False}
    return {"valid": True}


@router.post("/validate_name/", response_model=IsAnAttendee)
async def get_ticket_by_id(attendee: Attendee, response: Response):
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
            ticket = search_reference(attendee.ticket_id)[0]
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
        if ratio > 0.95:
            res["is_attendee"] = True
            res["hint"] = ""
        elif ratio > 0.8:
            res["is_attendee"] = False
            res["hint"] = f"Supplied name {attendee.name} is close but not close enough."
        else:
            res["is_attendee"] = False
            res["hint"] = f"We couldn't find {attendee.name}, check spelling."

    if "speaker" in ticket.get("release_title", "").lower():
        res["is_speaker"] = True
    if "organiser" in ticket.get("release_title", "").lower():
        res["is_organizer"] = True
        if attendee.ticket_id.upper() in CONFIG.organizer_speakers:
            res["is_speaker"] = True
    if "sponsor" in ticket.get("release_title", "").lower():
        res["is_sponsor"] = True
    if "volunteer" in ticket.get("release_title", "").lower():
        res["is_volunteer"] = True
    if ticket["release_id"] in interface.activity_release_id_map["remote_sale"]:
        res["is_remote"] = True
    if ticket["release_id"] in interface.activity_release_id_map["on_site"]:
        res["is_onsite"] = True
    if ticket["release_id"] in interface.activity_release_id_map["online_access"]:
        res["online_access"] = True
    return res

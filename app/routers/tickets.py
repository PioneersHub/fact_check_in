import json
import re
from difflib import SequenceMatcher

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field
from starlette import status
from unidecode import unidecode

from app.config import CONFIG
from app.tito.tito_api import get_all_tickets, get_all_ticket_offers

router = APIRouter(prefix="/tickets", tags=["Attendees"])

all_sales = {}
all_releases = {}


class Attendee(BaseModel):
    ticket_id: str = Field(..., example="XRTP-3", description="Tito ticket ID is a four char alphanumeric -  integer.")
    name: str = Field(..., example="Sam Smith", description="Person full name as used for registration.")


class IsAnAttendee(Attendee):
    is_attendee: bool = Field(
        ..., example=False, description="Returns if the combination od ticket ID and name is valid."
    )
    hint: str = Field(
        "",
        example="Looks like a typo",
        description="Hint why validation failed, eg. if the name is close but not close enough.",
    )


def exclude_this_ticket_type(ticket_name: str):
    """Filter by ticket name substrings"""
    for pattern in CONFIG.exclude_ticket_patterns:
        if pattern.lower() in ticket_name.lower():
            return True


def valid_ticket_types(data):
    """List of qualified ticket types (releases)"""
    return [x for x in data if not exclude_this_ticket_type(x["title"])]


def normalization(txt):
    """Remove all diacritic marks, normalize everything to asci, and make all upper case"""
    txt = re.sub(r"\s{2,}", " ", txt).strip()
    return unidecode(txt).upper()


@router.get("/refresh_all/")
def refresh_all():
    """
    Service method to force a reload of all ticket data from the ticketing system
    """
    global all_sales
    global all_releases
    res = get_all_tickets(from_cache=False)
    all_sales = {x["reference"].upper(): x for x in  res}
    res = get_all_ticket_offers()
    all_releases = {x["title"].upper(): x for x in res}
    return {"message": "The ticket cache was refreshed successfully."}


@router.get("/ticket_types/")
async def get_ticket_types():
    _file = CONFIG.datadir / "ticket_offers.json"
    data = json.load(_file.open())
    return data


@router.post("/validate_name/", response_model=IsAnAttendee)
async def get_ticket_by_id(attendee: Attendee, response: Response):
    """
    Validate an attendee by:
      - ticket id
      - name
    """
    res = attendee.dict()
    try:
        ticket = all_sales[attendee.ticket_id]
    except KeyError:
        response.status_code = status.HTTP_404_NOT_FOUND
        res["is_attendee"] = False
        res["hint"] = "invalid ticket id"
        return res

    if exclude_this_ticket_type(ticket["release_title"]):
        response.status_code = status.HTTP_406_NOT_ACCEPTABLE
        res["is_attendee"] = True
        res["hint"] = f"invalid ticket type: {ticket['release_title']}"
        return res

    if ticket["name"].strip().upper() == attendee.name.strip().upper():
        res["is_attendee"] = True
    else:
        ratio = SequenceMatcher(
            None, normalization(ticket["name"]), normalization(attendee.name)
        ).ratio()
        if ratio > 0.95:
            res["is_attendee"] = True
            res["hint"] = ""
        elif ratio > 0.8:
            res["is_attendee"] = False
            res["hint"] = f"Supplied name {attendee.name} is close but not close enough."
        else:
            res["is_attendee"] = False
            res["hint"] = f"Incorrect name specified"
    return res

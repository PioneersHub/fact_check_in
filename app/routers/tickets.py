import json

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field
from starlette import status

from app.config import CONFIG
from app.tito.tito_api import get_all_tickets, get_all_ticket_offers

router = APIRouter(prefix="/tickets", tags=["Attendees"])

all_sales = {}
all_releases = {}


class Attendee(BaseModel):
    ticket_id: str = Field(..., example="XRTP-3", description="Tito ticket ID is a four char alphanumeric -  integer.")
    last_name: str = Field(..., example="Smith", description="Person last name.")


class IsAnAttendee(Attendee):
    is_attendee: bool = Field(
        ..., example=False, description="Returns if the combination od ticket ID and last name is valid."
    )
    hint: str = Field(
        "",
        example="Looks like a typo",
        description="Hint why validation failed, eg. if the name is close but not close enough.",
    )


def exclude_this_ticket_type(ticket_name: str):
    """ Filter by ticket name substrings """
    for pattern in CONFIG.exclude_ticket_patterns:
        if pattern.lower() in ticket_name.lower():
            return True


def valid_ticket_types(data):
    """List of qualified ticket types (releases)"""
    return [x for x in data if not exclude_this_ticket_type(x["title"])]


@router.get("/refresh_all/")
async def refresh_all():
    """
    Service method to force a reload of all ticket data from the ticketing system
    """
    global all_sales
    global all_releases
    all_sales = {x["reference"].upper(): x for x in await get_all_tickets(from_cache=False)}
    all_releases = {x["title"].upper(): x for x in await get_all_ticket_offers()}
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
      - last name
    """
    res = attendee.dict()
    try:
        ticket = all_sales[attendee.ticket_id]
    except KeyError:
        await refresh_all()
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

    if ticket["last_name"].strip().upper() == attendee.last_name.strip().upper():
        res["is_attendee"] = True
        return res

    # TODO:
    #  add some fuzzy logic esp. handling non ascii chars, double spaces etc
    return attendee

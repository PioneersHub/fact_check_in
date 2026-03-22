"""Pretix-specific routes."""

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Response
from starlette import status

from app import interface, log
from app.config import CONFIG
from app.models.base import Email, Truthy
from app.routers.common import refresh_all
from app.ticketing.backend import get_ticketing_backend
from app.ticketing.utils import fuzzy_match_name

if TYPE_CHECKING:
    from app.pretix.backend import PretixBackend

from .addon_stats import get_addon_statistics, load_addon_statistics
from .models import AddonStatistics, PretixAttendee, PretixIsAnAttendee

router = APIRouter(prefix="/tickets", tags=["Pretix Validation"])


@router.post("/validate_email/", response_model=Truthy)
async def search_email(email: Email, response: Response):  # noqa: ARG001
    """Search for a participant by email in preloaded orders."""
    req = email.model_dump()
    log.debug(email)
    log.debug(f"searching for email: {req['email']}")
    backend: PretixBackend = get_ticketing_backend()  # type: ignore[assignment]
    if req["email"] in backend.api.interface.valid_emails:
        return {"valid": True}
    # Email not found in cache - force a refresh and try again.
    # Pretix does have an email search endpoint but refreshing all data
    # is simpler and keeps the cached data current.
    refresh_all()
    if req["email"] in backend.api.interface.valid_emails:
        return {"valid": True}
    raise HTTPException(status_code=404, detail="Email not found")


@router.post("/validate_attendee/", response_model=PretixIsAnAttendee)
async def validate_pretix_attendee(attendee: PretixAttendee, response: Response):
    """Validate a Pretix attendee.

    Supports flexible validation options:
    - Order ID + Name, Ticket ID (secret) + Name,
    - Order ID + Name + Ticket ID (most secure).
    """
    res: dict = attendee.model_dump()
    valid_order = False
    # noinspection PyBroadException
    try:
        item = interface.valid_order_name_combo.get((attendee.order_id, attendee.name.strip().upper()))
        if item:
            # direct hit, can be processed directly
            return detailed_positive_result(item)
    except Exception as e:  # noqa: BLE001
        log.warning("error looking up attendee", error=str(e))
    valid_order = bool(attendee.order_id) and attendee.order_id.upper() in interface.valid_order_ids  # type: ignore[union-attr]

    if not valid_order:
        response.status_code = status.HTTP_404_NOT_FOUND
        res["is_attendee"] = False
        # noinspection PyTypeChecker
        res["hint"] = "Invalid order ID, must be five alphanumeric chars like 'HLL1H'"
        return res

    # Find position(s) matching the name
    matching_positions = []
    for name in [name_ for order_id, name_ in interface.valid_order_name_combo if order_id == attendee.order_id]:
        match_result = fuzzy_match_name(
            name,
            attendee.name,
            CONFIG.name_matching.exact_match_threshold,
            CONFIG.name_matching.close_match_threshold,
        )
        if match_result["is_match"]:
            item = interface.valid_order_name_combo[(attendee.order_id, name)]
            matching_positions.append((name, match_result, item))
        elif match_result["is_close"]:
            matching_positions.append((name, match_result, {}))

    if not matching_positions:
        response.status_code = status.HTTP_404_NOT_FOUND
        res["is_attendee"] = False
        res["hint"] = f"No attendee named '{attendee.name}' found on order {attendee.order_id}"
        return res

    for _, match_result, item in matching_positions:
        if match_result["is_match"]:
            return detailed_positive_result(item)
    for _, match_result, _ in matching_positions:
        if match_result["is_close"]:
            response.status_code = status.HTTP_406_NOT_ACCEPTABLE
            res["is_attendee"] = False
            res["hint"] = f"Name '{attendee.name}' is close but not exact enough."
            return res
    response.status_code = status.HTTP_404_NOT_FOUND
    res["is_attendee"] = False
    res["hint"] = f"No attendee named '{attendee.name}' found on order {attendee.order_id}"
    return res


@router.get("/addon_statistics/", response_model=AddonStatistics, tags=["Pretix Statistics"])
async def addon_statistics():
    """Return add-on product statistics from cached data.

    Provides metrics about on-site ticket sales and Conference T-Shirt add-on purchases.
    Data is loaded on startup and can be refreshed via /tickets/refresh_addon_statistics/.
    """
    return get_addon_statistics()


@router.get("/refresh_addon_statistics/", response_model=AddonStatistics, tags=["Pretix Statistics"])
async def refresh_addon_statistics():
    """Refresh add-on statistics cache from Pretix API and return updated data."""
    load_addon_statistics()
    return get_addon_statistics()


def detailed_positive_result(item) -> dict[str, bool]:
    """Build a detailed positive result dict from a matched ticket item.

    Sets attributes to True if matched, never to False.
    """
    res = {"name": item["name"], "order_id": item["order"], "is_attendee": True}

    # add ticket features via categories.by_id
    _attributes = interface.release_id_map[item["item"]]["_attributes"]
    res.update(_attributes)
    # add ticket features categories.by_ticket_id
    _attributes = CONFIG.pretix_mapping.categories.by_ticket_id.get(item["item"], {})
    res.update(_attributes)
    # add ticket ticker_id + pos:
    #  - organizer_and_speaker
    if item["reference"] in CONFIG.pretix_mapping.organizer_and_speaker:
        res.update({"is_speaker": True, "is_organizer": True})
    #  - organizer_and_sponsor
    if item["reference"] in CONFIG.pretix_mapping.organizer_and_sponsor:
        res.update({"is_sponsor": True, "is_organizer": True})
    #  - speaker_and_sponsor
    if item["reference"] in CONFIG.pretix_mapping.speaker_and_sponsor:
        res.update({"is_speaker": True, "is_sponsor": True})
    #  - speaker_add_keynote
    if item["reference"] in CONFIG.pretix_mapping.speaker_add_keynote:
        res.update({"is_speaker": True, "is_keynote": True})
    if item["reference"] in CONFIG.pretix_mapping.add_speaker:
        res.update({"is_speaker": True})
    return res

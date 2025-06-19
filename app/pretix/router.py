"""Pretix-specific routes."""

from fastapi import APIRouter, Response
from starlette import status

from app import interface
from app.config import CONFIG
from app.ticketing.utils import fuzzy_match_name

from .models import PretixAttendee, PretixIsAnAttendee
from .pretix_api import search_by_order, search_by_secret

router = APIRouter(prefix="/tickets", tags=["Pretix Validation"])


@router.post("/validate_attendee/", response_model=PretixIsAnAttendee)
async def validate_pretix_attendee(attendee: PretixAttendee, response: Response):  # noqa: PLR0911, PLR0912, PLR0915
    """
    Validate Pretix attendee with flexible validation options:
    - Order ID + Name
    - Ticket ID (secret) + Name
    - Order ID + Name + Ticket ID (most secure)
    """
    res = attendee.model_dump()
    position = None

    # Priority: secret (most specific) -> order lookup
    if attendee.ticket_id:
        # Search by secret
        position = search_by_secret(attendee.ticket_id)
        if not position:
            response.status_code = status.HTTP_404_NOT_FOUND
            res["is_attendee"] = False
            res["hint"] = "Invalid ticket ID"
            return res

        # If order_id also provided, verify they match
        if attendee.order_id:
            # Extract order code from reference (e.g., "ABC23-1" -> "ABC23")
            order_part = position["reference"].split("-")[0]
            if order_part != attendee.order_id.upper():
                response.status_code = status.HTTP_406_NOT_ACCEPTABLE
                res["is_attendee"] = False
                res["hint"] = "Order ID and Ticket ID do not match"
                return res

    elif attendee.order_id:
        # Only order_id provided - search all positions for this order
        positions = search_by_order(attendee.order_id)

        if not positions:
            response.status_code = status.HTTP_404_NOT_FOUND
            res["is_attendee"] = False
            res["hint"] = "Invalid order ID"
            return res

        # Find position(s) matching the name
        matching_positions = []
        for pos in positions:
            match_result = fuzzy_match_name(
                pos.get("name", ""),
                attendee.name,
                CONFIG.name_matching.exact_match_threshold,
                CONFIG.name_matching.close_match_threshold,
            )
            if match_result["is_match"]:
                matching_positions.append((pos, match_result))

        if not matching_positions:
            # Check if any names were close
            close_matches = []
            for pos in positions:
                match_result = fuzzy_match_name(
                    pos.get("name", ""),
                    attendee.name,
                    CONFIG.name_matching.exact_match_threshold,
                    CONFIG.name_matching.close_match_threshold,
                )
                if match_result["is_close"]:
                    close_matches.append(pos)

            if close_matches:
                response.status_code = status.HTTP_406_NOT_ACCEPTABLE
                res["is_attendee"] = False
                res["hint"] = f"Name '{attendee.name}' is close but not exact enough"
                return res
            else:
                response.status_code = status.HTTP_404_NOT_FOUND
                res["is_attendee"] = False
                res["hint"] = f"No attendee named '{attendee.name}' found on order {attendee.order_id}"
                return res

        # Use best match (first one)
        position, match_info = matching_positions[0]
        if match_info.get("hint"):
            res["hint"] = match_info["hint"]

    # At this point we should have a position
    if not position:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        res["is_attendee"] = False
        res["hint"] = "Unexpected error"
        return res

    # Validate name match one more time if we found by secret
    if attendee.ticket_id and not attendee.order_id:
        match_result = fuzzy_match_name(
            position.get("name", ""),
            attendee.name,
            CONFIG.name_matching.exact_match_threshold,
            CONFIG.name_matching.close_match_threshold,
        )

        if not match_result["is_match"]:
            if match_result["is_close"]:
                response.status_code = status.HTTP_406_NOT_ACCEPTABLE
                res["is_attendee"] = False
                res["hint"] = match_result["hint"]
                return res
            else:
                response.status_code = status.HTTP_404_NOT_FOUND
                res["is_attendee"] = False
                res["hint"] = match_result["hint"]
                return res

    # Check if ticket type is valid
    if position["release_id"] not in interface.valid_ticket_ids:
        response.status_code = status.HTTP_406_NOT_ACCEPTABLE
        res["is_attendee"] = False
        try:
            release_title = interface.release_id_map[position["release_id"]]["title"]
            res["hint"] = f"invalid ticket type: {release_title}"
        except KeyError:
            res["hint"] = "invalid ticket type"
        return res

    # Success - set response
    res["is_attendee"] = True

    # Set attributes from release mapping
    release_info = interface.release_id_map.get(position["release_id"], {})
    if "_attributes" in release_info:
        attributes = release_info["_attributes"]
        res.update(
            {
                "is_speaker": attributes.get("is_speaker", False),
                "is_organizer": attributes.get("is_organizer", False),
                "is_sponsor": attributes.get("is_sponsor", False),
                "is_volunteer": attributes.get("is_volunteer", False),
                "is_guest": attributes.get("is_guest", False),
                "is_remote": attributes.get("is_remote", False),
                "is_onsite": attributes.get("is_onsite", False),
                "online_access": attributes.get("online_access", False),
            }
        )

        # Special case: check organizer speakers list
        if res["is_organizer"] and position.get("reference", "").upper() in CONFIG.organizer_speakers:
            res["is_speaker"] = True

    return res

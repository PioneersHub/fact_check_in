"""Pretix-specific routes."""

from fastapi import APIRouter, Response
from starlette import status

from app import interface
from app.config import CONFIG
from app.ticketing.utils import fuzzy_match_name

from .models import PretixAttendee, PretixIsAnAttendee
from .pretix_api import search_by_order

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

    # noinspection PyBroadException
    try:
        item = interface.valid_order_name_combo.get((attendee.order_id, attendee.name.strip().upper()))
        if item:
            # direct hit, can be processed directly
            res = detailed_positive_result(item)
            return res
        # valid_email = interface.valid_emails.get(attendee.email.strip().casefold())
        # TODO: allocated ticket with fuzzy name match

        valid_order = attendee.order_id.upper() in interface.valid_order_ids
        valid_name = attendee.name.strip().upper() in interface.valid_names
        _ = valid_order or valid_name

    except Exception as e:
        print(e)
        pass

    if attendee.order_id:
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
    return detailed_positive_result()


def base_result():
    return dict.fromkeys(
        {"is_attendee", "is_speaker", "is_organizer", "is_sponsor", "is_volunteer", "is_guest", "is_remote", "is_onsite", "online_access"},
        False,
    )


def detailed_positive_result(item) -> dict[str, bool]:
    """Set attributes via ticket and rules in CONFIG
    For clarity: set attributes to True if matched, never to False"""
    res = base_result()
    res["name"] = item["name"]
    res["order_id"] = item["order"]
    res["is_attendee"] = True

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
    return res

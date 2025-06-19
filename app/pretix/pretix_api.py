# Pretix API configuration
import os
from http import HTTPStatus

import requests
from fastapi.encoders import jsonable_encoder

from app import in_dummy_mode, interface, log
from app.errors import NotOk

PRETIX_TOKEN = os.getenv("PRETIX_TOKEN")
PRETIX_BASE_URL = os.getenv("PRETIX_BASE_URL", "https://pretix.eu/api/v1")
ORGANIZER_SLUG = os.getenv("PRETIX_ORGANIZER_SLUG")
EVENT_SLUG = os.getenv("PRETIX_EVENT_SLUG")

headers = {
    "Accept": "application/json",
    "Authorization": f"Token {PRETIX_TOKEN}" if PRETIX_TOKEN else "",
}

headers_post = dict(headers.items())
headers_post["Content-Type"] = "application/json"


def minimize_data(data: list[dict]) -> list[dict]:
    """Remove all data that is not relevant to run the application.

    For Pretix, we keep order position data that maps to ticket data in Tito.
    """
    opt_in_attributes = {
        "id",
        "order",  # Order code (like ABCD1)
        "positionid",  # Position within order
        "item",  # Product ID
        "variation",  # Product variation ID
        "attendee_name",
        "attendee_email",
        "secret",  # Ticket secret/barcode
        "pseudonymization_id",  # Unique attendee ID
        "state",  # Order state
        "created",
        "modified",
    }
    log.debug("minimizing data footprint")
    filtered = [{k: v for k, v in x.items() if k in opt_in_attributes} for x in data]
    return filtered


def filter_valid_items(data: list[dict], valid_item_ids: set) -> list[dict]:
    """Filter order positions by valid item IDs."""
    filtered = [x for x in data if x.get("item") in valid_item_ids]
    return filtered


def response_is_not_ok(response):
    content = "response is not OK"
    try:
        log.info("error", response.status_code)
        content = jsonable_encoder({response.status_code: response.json()})
    except Exception as e:
        log.info("error", e)
        content = jsonable_encoder({response.status_code: str(e)})
    finally:
        raise NotOk(status_code=response.status_code, content=content)  # noqa: B012


def get_all_order_positions():
    """Get all order positions (equivalent to tickets in Tito)."""
    if in_dummy_mode:
        return
    log.info("Loading all order positions from Pretix API")
    collect = []

    url = f"{PRETIX_BASE_URL}/organizers/{ORGANIZER_SLUG}/events/{EVENT_SLUG}/orderpositions/"
    params = {"page": 1}

    while True:
        log.info(f"getting page:{params['page']}")
        res = requests.get(url, headers=headers, params=params)
        if res.status_code != HTTPStatus.OK:
            response_is_not_ok(res)

        res_j = res.json()
        # Transform Pretix data to match Tito structure
        positions = []
        for pos in res_j["results"]:
            # Create a reference like Tito's "ABCD-1" from order + position
            reference = f"{pos['order']}-{pos['positionid']}"

            transformed = {
                "reference": reference.upper(),
                "email": pos.get("attendee_email", ""),
                "name": pos.get("attendee_name", "") or pos.get("attendee_name_cached", ""),
                "release_id": pos["item"],  # Map item ID to release_id
                "state": "complete" if pos.get("order__status") == "p" else "pending",
                "created_at": pos.get("created"),
                "updated_at": pos.get("modified"),
                "assigned": bool(pos.get("attendee_email")),
                # Store original Pretix data for reference
                "_pretix_data": {
                    "order": pos["order"],
                    "positionid": pos["positionid"],
                    "secret": pos.get("secret"),
                    "item": pos["item"],
                    "variation": pos.get("variation"),
                },
            }
            positions.append(transformed)

        data = minimize_data(positions)
        collect.extend(data)

        if res_j["next"]:
            params["page"] += 1
        else:
            break

    interface.all_sales = {x["reference"]: x for x in collect}


def get_all_items():
    """Get all items/products (equivalent to releases/ticket types in Tito)."""
    if in_dummy_mode:
        return
    collect = []

    url = f"{PRETIX_BASE_URL}/organizers/{ORGANIZER_SLUG}/events/{EVENT_SLUG}/items/"
    params = {"page": 1}

    while True:
        log.info(f"getting page:{params['page']}")
        res = requests.get(url, headers=headers, params=params)
        if res.status_code != HTTPStatus.OK:
            response_is_not_ok(res)

        res_j = res.json()

        for item in res_j["results"]:
            # Transform Pretix items to match Tito releases structure
            transformed = {
                "id": item["id"],
                "title": item["name"].get("en", item["name"]),  # Handle multi-language
                # Pretix doesn't have activities, so we determine type from name/category
                "activities": determine_activities_from_item(item),
            }
            collect.append(transformed)

        if res_j["next"]:
            params["page"] += 1
        else:
            break

    interface.all_releases = {x["title"].upper(): x for x in collect}


def determine_activities_from_item(item: dict) -> list[str]:
    """Determine pseudo-activities based on item name and category.

    This maps Pretix items to the activity-based system used by Tito.
    """
    activities = []
    name = item.get("name", {}).get("en", "").lower()

    # Check for online/remote indicators
    if any(keyword in name for keyword in ["online", "remote", "virtual", "streaming"]):
        activities.extend(["remote_sale", "online_access"])

    # Check for in-person indicators
    if any(keyword in name for keyword in ["in-person", "on-site", "physical", "venue"]):
        activities.extend(["on_site", "online_access"])  # Most include online access too

    # Check for day passes
    if "day pass" in name:
        activities.append("on_site")
        if "monday" in name:
            activities.append("seat-person-monday")
        if "tuesday" in name:
            activities.append("seat-person-tuesday")
        if "wednesday" in name:
            activities.append("seat-person-wednesday")
        activities.append("online_access")

    # Default: if no specific indicators, assume it's an on-site ticket with online access
    if not activities:
        activities = ["on_site", "online_access"]

    return activities


def search_reference(reference):
    """Search for a specific order position by reference."""
    log.debug(f"searching for reference: {reference}")
    if in_dummy_mode:
        res = interface.all_sales.get(reference)
        return res

    # Split reference back into order and position
    try:
        order_code, position_id = reference.upper().split("-")
        position_id = int(position_id)
    except ValueError:
        log.debug(f"Invalid reference format: {reference}")
        return None

    # Search for the specific order position
    url = f"{PRETIX_BASE_URL}/organizers/{ORGANIZER_SLUG}/events/{EVENT_SLUG}/orderpositions/"
    params = {
        "order__code": order_code,
    }

    res = requests.get(url, headers=headers, params=params)
    if res.status_code != HTTPStatus.OK:
        log.debug(f"the request reference: {reference} returned status code: {res.status_code}")
        response_is_not_ok(res)

    res_j = res.json()

    # Find the specific position
    for pos in res_j["results"]:
        if pos["positionid"] == position_id:
            # Transform to match Tito structure
            return [
                {
                    "reference": reference,
                    "email": pos.get("attendee_email", ""),
                    "name": pos.get("attendee_name", "") or pos.get("attendee_name_cached", ""),
                    "release_id": pos["item"],
                    "state": "complete" if pos.get("order__status") == "p" else "pending",
                }
            ]

    log.debug(f"Position {position_id} not found in order {order_code}")
    return []


def search(search_for: str):
    """Search for attendees by email or name."""
    log.debug(f"searching for {search_for}")
    if in_dummy_mode:
        res = [x for x in interface.all_sales.values() if search_for.casefold().strip() in x["email"].casefold().strip()]
        if res:
            return res
        return [{"email": search_for}]

    # Pretix allows searching by attendee email or name
    url = f"{PRETIX_BASE_URL}/organizers/{ORGANIZER_SLUG}/events/{EVENT_SLUG}/orderpositions/"

    # Try email search first
    params = {"attendee_email__icontains": search_for}
    res = requests.get(url, headers=headers, params=params)

    if res.status_code != HTTPStatus.OK:
        log.debug(f"the request {search_for} returned status code: {res.status_code}")
        response_is_not_ok(res)

    res_j = res.json()
    results = []

    # Transform results
    for pos in res_j["results"]:
        reference = f"{pos['order']}-{pos['positionid']}"
        results.append(
            {
                "reference": reference.upper(),
                "email": pos.get("attendee_email", ""),
                "name": pos.get("attendee_name", "") or pos.get("attendee_name_cached", ""),
                "release_id": pos["item"],
                "state": "complete" if pos.get("order__status") == "p" else "pending",
            }
        )

    # If no results, try name search
    if not results:
        params = {"attendee_name__icontains": search_for}
        res = requests.get(url, headers=headers, params=params)

        if res.status_code == HTTPStatus.OK:
            res_j = res.json()
            for pos in res_j["results"]:
                reference = f"{pos['order']}-{pos['positionid']}"
                results.append(
                    {
                        "reference": reference.upper(),
                        "email": pos.get("attendee_email", ""),
                        "name": pos.get("attendee_name", "") or pos.get("attendee_name_cached", ""),
                        "release_id": pos["item"],
                        "state": "complete" if pos.get("order__status") == "p" else "pending",
                    }
                )

    log.debug(f"success: the request {search_for} returned {len(results)} tickets.")
    return results


# Map Pretix functions to Tito function names for compatibility
get_all_tickets = get_all_order_positions
get_all_ticket_offers = get_all_items


if __name__ == "__main__":
    pass

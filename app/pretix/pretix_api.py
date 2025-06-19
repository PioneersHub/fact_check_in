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
        "reference",  # Our constructed reference (ORDER-POSITION)
        "email",  # Mapped from attendee_email
        "name",  # Mapped from attendee_name
        "release_id",  # Mapped from item
        "state",  # Mapped from order status
        "created_at",  # Mapped from created
        "updated_at",  # Mapped from modified
        "assigned",  # Based on attendee_email presence
        "_pretix_data",  # Original Pretix data
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


def get_all_categories():
    """Get all categories from Pretix."""
    if in_dummy_mode:
        return {}

    categories = {}
    url = f"{PRETIX_BASE_URL}/organizers/{ORGANIZER_SLUG}/events/{EVENT_SLUG}/categories/"
    params = {"page": 1}

    while True:
        log.info(f"getting categories page:{params['page']}")
        res = requests.get(url, headers=headers, params=params)
        if res.status_code != HTTPStatus.OK:
            response_is_not_ok(res)

        res_j = res.json()
        for cat in res_j["results"]:
            categories[cat["id"]] = {
                "id": cat["id"],
                "name": cat["name"].get("en", cat["name"]) if isinstance(cat["name"], dict) else cat["name"],
                "internal_name": cat.get("internal_name", ""),
            }

        if res_j["next"]:
            params["page"] += 1
        else:
            break

    return categories


def get_all_items():
    """Get all items/products (equivalent to releases/ticket types in Tito)."""
    if in_dummy_mode:
        return

    # First fetch categories
    categories = get_all_categories()
    interface.categories = categories  # Store for validation

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
            # Determine activities first (which also sets _attributes)
            activities = determine_activities_from_item(item, categories)

            # Transform Pretix items to match Tito releases structure
            transformed = {
                "id": item["id"],
                "title": item["name"].get("en", item["name"]),  # Handle multi-language
                "category_id": item.get("category"),
                "category": categories.get(item.get("category"), {}) if item.get("category") else None,
                "activities": activities,
                # Copy the attributes that were set during activity determination
                "_attributes": item.get("_attributes", {}),
            }
            collect.append(transformed)

        if res_j["next"]:
            params["page"] += 1
        else:
            break

    interface.all_releases = {x["title"].upper(): x for x in collect}


def determine_activities_from_item(item: dict, categories: dict = None) -> list[str]:
    """Determine pseudo-activities based on item name and category.

    This maps Pretix items to the activity-based system used by Tito.
    """
    from app.pretix.mapping import PretixAttributeMapper

    # Get the mapper
    mapper = PretixAttributeMapper()

    # Get category info if available
    category = None
    if categories and item.get("category"):
        category = categories.get(item["category"])

    # Get attributes using the mapping engine
    attributes = mapper.get_attributes_from_item(item, category)

    # Store attributes in the item for later use (e.g., in validation endpoint)
    item["_attributes"] = attributes

    # Convert to legacy activities format
    activities = mapper.get_activities_from_attributes(attributes)

    # Add day-specific activities if it's a day pass
    name = item.get("name", {}).get("en", "").lower()
    if "day pass" in name:
        if "monday" in name:
            activities.append("seat-person-monday")
        if "tuesday" in name:
            activities.append("seat-person-tuesday")
        if "wednesday" in name:
            activities.append("seat-person-wednesday")

    # Ensure we have at least some activities
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
        # Only include if email actually matches
        if pos.get("attendee_email") and search_for.lower() in pos.get("attendee_email", "").lower():
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
                # Only include if name actually matches
                if pos.get("attendee_name") and search_for.lower() in pos.get("attendee_name", "").lower():
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


def search_by_secret(secret: str):
    """Search for order position by secret/ticket ID."""
    log.debug(f"searching by secret: {secret}")
    if in_dummy_mode:
        # Find by secret in _pretix_data
        for sale in interface.all_sales.values():
            if sale.get("_pretix_data", {}).get("secret") == secret:
                return sale
        return None

    url = f"{PRETIX_BASE_URL}/organizers/{ORGANIZER_SLUG}/events/{EVENT_SLUG}/orderpositions/"
    params = {"secret": secret}

    res = requests.get(url, headers=headers, params=params)
    if res.status_code != HTTPStatus.OK:
        log.debug(f"search by secret returned status code: {res.status_code}")
        return None

    res_j = res.json()
    results = res_j.get("results", [])

    if results:
        # Transform and return first match
        pos = results[0]
        reference = f"{pos['order']}-{pos['positionid']}"
        return {
            "reference": reference.upper(),
            "email": pos.get("attendee_email", ""),
            "name": pos.get("attendee_name", "") or pos.get("attendee_name_cached", ""),
            "release_id": pos["item"],
            "state": "complete" if pos.get("order__status") == "p" else "pending",
            "created_at": pos.get("created"),
            "updated_at": pos.get("modified"),
            "assigned": bool(pos.get("attendee_email")),
            "_pretix_data": {
                "order": pos["order"],
                "positionid": pos["positionid"],
                "secret": pos.get("secret"),
                "item": pos["item"],
                "variation": pos.get("variation"),
            },
        }
    return None


def search_by_order(order_code: str):
    """Search for all order positions by order code."""
    log.debug(f"searching by order: {order_code}")
    if in_dummy_mode:
        # Find all positions for this order
        results = []
        for sale in interface.all_sales.values():
            if sale.get("_pretix_data", {}).get("order") == order_code.upper():
                results.append(sale)
        return results

    url = f"{PRETIX_BASE_URL}/organizers/{ORGANIZER_SLUG}/events/{EVENT_SLUG}/orderpositions/"
    params = {"order": order_code}

    res = requests.get(url, headers=headers, params=params)
    if res.status_code != HTTPStatus.OK:
        log.debug(f"search by order returned status code: {res.status_code}")
        return []

    res_j = res.json()
    results = []

    # Transform all positions
    for pos in res_j.get("results", []):
        reference = f"{pos['order']}-{pos['positionid']}"
        results.append(
            {
                "reference": reference.upper(),
                "email": pos.get("attendee_email", ""),
                "name": pos.get("attendee_name", "") or pos.get("attendee_name_cached", ""),
                "release_id": pos["item"],
                "state": "complete" if pos.get("order__status") == "p" else "pending",
                "created_at": pos.get("created"),
                "updated_at": pos.get("modified"),
                "assigned": bool(pos.get("attendee_email")),
                "_pretix_data": {
                    "order": pos["order"],
                    "positionid": pos["positionid"],
                    "secret": pos.get("secret"),
                    "item": pos["item"],
                    "variation": pos.get("variation"),
                },
            }
        )

    return results


# Map Pretix functions to Tito function names for compatibility
get_all_tickets = get_all_order_positions
get_all_ticket_offers = get_all_items


if __name__ == "__main__":
    pass

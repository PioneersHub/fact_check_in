"""Add-on product statistics for Pretix events.

Fetches and caches add-on order position data from the Pretix API,
then computes statistics about on-site ticket sales and T-shirt add-ons.
"""

from collections import Counter
from http import HTTPStatus

import requests

from app import in_dummy_mode, interface, log
from app.config import CONFIG
from app.pretix.models import AddonStatistics, TShirtVariantCount
from app.pretix.pretix_api import (
    EVENT_SLUG,
    ORGANIZER_SLUG,
    PRETIX_BASE_URL,
    headers,
    response_is_not_ok,
)


def _fetch_all_pages(url: str, params: dict) -> list[dict]:
    """Fetch all pages from a paginated Pretix API endpoint."""
    collect = []
    params = {**params, "page": 1}

    while True:
        log.info(f"fetching page:{params['page']} from {url}")
        res = requests.get(url, headers=headers, params=params, timeout=30)
        if res.status_code != HTTPStatus.OK:
            response_is_not_ok(res)

        res_j = res.json()
        collect.extend(res_j["results"])

        if res_j["next"]:
            params["page"] += 1
        else:
            break

    return collect


def _fetch_item_variations(item_id: int) -> dict[int, str]:
    """Fetch variation names for a specific item.

    Returns a mapping of variation ID to human-readable name.
    """
    url = f"{PRETIX_BASE_URL}/organizers/{ORGANIZER_SLUG}/events/{EVENT_SLUG}/items/{item_id}/variations/"
    results = _fetch_all_pages(url, {})

    variations = {}
    for var in results:
        name = var["value"]
        if isinstance(name, dict):
            name = name.get("en", next(iter(name.values())))
        variations[var["id"]] = name

    return variations


def _fetch_addon_positions(item_id: int) -> list[dict]:
    """Fetch all order positions for a specific add-on item.

    Returns minimal position data needed for statistics.
    Fetches paid (p) and pending (n) orders separately and combines them,
    excluding cancelled orders.
    """
    url = f"{PRETIX_BASE_URL}/organizers/{ORGANIZER_SLUG}/events/{EVENT_SLUG}/orderpositions/"
    results = _fetch_all_pages(url, {"item": item_id, "order__status": "p"}) + _fetch_all_pages(
        url, {"item": item_id, "order__status": "n"}
    )

    positions = []
    for pos in results:
        if pos.get("canceled"):
            continue
        positions.append(
            {
                "id": pos["id"],
                "order": pos["order"],
                "positionid": pos["positionid"],
                "item": pos["item"],
                "variation": pos.get("variation"),
                "addon_to": pos.get("addon_to"),
            },
        )

    return positions


def load_addon_statistics() -> None:
    """Fetch add-on data from Pretix API and cache it in the Interface singleton.

    Must be called after refresh_all() so that interface.all_sales and
    interface.release_id_map are already populated.
    """
    if in_dummy_mode:
        log.info("Skipping add-on statistics loading in dummy mode")
        return

    tshirt_item_id = CONFIG.addon_statistics.tshirt_item_id
    log.info("Loading add-on statistics from Pretix API")

    interface.item_variations = _fetch_item_variations(tshirt_item_id)
    log.info(f"Loaded {len(interface.item_variations)} T-shirt variations")

    interface.addon_positions = _fetch_addon_positions(tshirt_item_id)
    log.info(f"Loaded {len(interface.addon_positions)} T-shirt add-on positions")


def get_addon_statistics() -> AddonStatistics:
    """Compute add-on statistics from cached data.

    Returns metrics about on-site ticket sales and T-shirt add-on purchases.
    """
    onsite_category_ids = set(CONFIG.addon_statistics.onsite_category_ids)

    # Count on-site tickets from cached sales data
    onsite_item_ids = {
        item_id for item_id, release in interface.release_id_map.items() if release.get("category_id") in onsite_category_ids
    }
    onsite_tickets = [sale for sale in interface.all_sales.values() if sale.get("item") in onsite_item_ids]
    onsite_tickets_sold = len(onsite_tickets)

    # Determine which on-site positions have a T-shirt add-on
    # addon_to references the internal position ID of the parent
    parent_ids_with_tshirt = {pos["addon_to"] for pos in interface.addon_positions if pos.get("addon_to") is not None}
    tshirt_purchased = len(parent_ids_with_tshirt)
    tshirt_not_purchased = onsite_tickets_sold - tshirt_purchased

    # Count variants
    variation_counts = Counter(pos["variation"] for pos in interface.addon_positions if pos.get("variation") is not None)
    tshirt_variants = [
        TShirtVariantCount(
            variant_name=interface.item_variations.get(var_id, f"Unknown ({var_id})"),
            count=count,
        )
        for var_id, count in sorted(variation_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    return AddonStatistics(
        onsite_tickets_sold=onsite_tickets_sold,
        tshirt_purchased=tshirt_purchased,
        tshirt_not_purchased=tshirt_not_purchased,
        tshirt_variants=tshirt_variants,
    )

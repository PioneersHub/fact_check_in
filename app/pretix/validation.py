"""Startup validation for Pretix attribute mappings."""

import os

from app import interface, log
from app.pretix.mapping import PretixAttributeMapper

# Constants
SMALL_ITEM_COUNT_THRESHOLD = 3  # Show details for up to this many items


def validate_pretix_mappings():
    """Validate Pretix attribute mappings on startup and log warnings."""
    # Only run for Pretix backend
    backend_name = os.environ.get("TICKETING_BACKEND")
    if backend_name.lower() != "pretix":
        return

    log.info("=" * 60)
    log.info("Validating Pretix attribute mappings...")

    # Get mapper and validate
    mapper = PretixAttributeMapper()

    # Get all items and categories from interface
    items = list(interface.all_releases.values()) if hasattr(interface, "all_releases") else []
    categories = getattr(interface, "categories", {})

    if not items:
        log.warning("No items found - skipping validation")
        return

    # Run validation
    report = mapper.validate_attribute_coverage(items, categories)

    # Log results
    _log_validation_results(report, mapper, categories)


def _log_validation_results(report: dict, mapper: PretixAttributeMapper, categories: dict):  # noqa: ARG001
    """Log validation results in a structured way."""
    # Log categories found
    log.info(f"Found {len(categories)} categories, {report['total_items']} items")
    for cat in report["categories_found"]:
        log.info(f"  Category: {cat.get('name', 'Unknown')} (ID: {cat.get('id')})")
    log.info("=" * 60)


def log_attribute_mapping_decisions(item_name: str, attributes: dict[str, bool], source: str):
    """Log mapping decisions for debugging.

    Args:
        item_name: Name of the item being mapped
        attributes: Attributes assigned
        source: Source of the mapping (e.g., "category_id", "category_name", "product_name")
    """
    log.debug(f"Mapped '{item_name}' via {source}: {attributes}")

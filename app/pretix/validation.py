"""Startup validation for Pretix attribute mappings."""

from app import interface, log
from app.pretix.mapping import PretixAttributeMapper

# Constants
SMALL_ITEM_COUNT_THRESHOLD = 3  # Show details for up to this many items


def validate_pretix_mappings():
    """Validate Pretix attribute mappings on startup and log warnings."""
    # Only run for Pretix backend
    import os

    from app.config import CONFIG

    backend_name = os.environ.get("TICKETING_BACKEND") or CONFIG.get("TICKETING_BACKEND", "tito")
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


def _log_validation_results(report: dict, mapper: PretixAttributeMapper, categories: dict):
    """Log validation results in a structured way."""
    # Log categories found
    log.info(f"Found {len(categories)} categories, {report['total_items']} items")
    for cat in report["categories_found"]:
        log.info(f"  Category: {cat.get('name', 'Unknown')} (ID: {cat.get('id')})")

    # Log warnings for unmapped attributes
    if report["unmapped_attributes"]:
        _log_unmapped_attributes(report["unmapped_attributes"])

    # Log attribute coverage summary
    _log_coverage_summary(report["coverage_stats"], mapper)

    # Suggestions for improvement
    if report["unmapped_attributes"]:
        log.info("💡 To improve attribute mapping:")
        log.info("   1. Add category mappings in app/config/base.yml under pretix_mapping.categories")
        log.info("   2. Create categories in Pretix matching the expected names")
        log.info("   3. Use product names that include keywords like 'speaker', 'sponsor', etc.")

    log.info("=" * 60)


def _log_unmapped_attributes(unmapped_attributes: list):
    """Log unmapped attributes with suggestions."""
    log.warning("⚠️  The following attributes have NO tickets mapped to them:")

    suggestions = {
        "is_speaker": "Create a 'Speaker' category in Pretix or add 'speaker' to product names",
        "is_sponsor": "Create a 'Sponsor' category in Pretix or add 'sponsor' to product names",
        "is_organizer": "Create an 'Organizer' category in Pretix or add 'organizer' to product names",
        "is_volunteer": "Create a 'Volunteer' category in Pretix or add 'volunteer' to product names",
        "is_guest": "Create a 'VIP' or 'Guest' category in Pretix",
    }

    for attr in unmapped_attributes:
        log.warning(f"  ❌ {attr}")
        if attr in suggestions:
            log.info(f"     → Suggestion: {suggestions[attr]}")


def _log_coverage_summary(coverage_stats: dict, mapper: PretixAttributeMapper):
    """Log attribute coverage summary."""
    log.info("Attribute coverage summary:")
    covered_count = 0

    for attr, stats in coverage_stats.items():
        if stats["count"] > 0:
            covered_count += 1
            log.info(f"  ✅ {attr}: {stats['count']} tickets ({stats['percentage']:.1f}%)")
            # Log which tickets map to this attribute
            if stats["count"] <= SMALL_ITEM_COUNT_THRESHOLD:
                for item in stats["items"]:
                    log.debug(f"      - {item}")
        else:
            log.info(f"  ❌ {attr}: 0 tickets (0.0%)")

    # Overall coverage
    coverage_percentage = (covered_count / len(mapper.all_attributes)) * 100 if mapper.all_attributes else 0
    log.info(f"Overall attribute coverage: {covered_count}/{len(mapper.all_attributes)} ({coverage_percentage:.1f}%)")


def log_attribute_mapping_decisions(item_name: str, attributes: dict[str, bool], source: str):
    """Log mapping decisions for debugging.

    Args:
        item_name: Name of the item being mapped
        attributes: Attributes assigned
        source: Source of the mapping (e.g., "category_id", "category_name", "product_name")
    """
    log.debug(f"Mapped '{item_name}' via {source}: {attributes}")

"""Mapping engine for Pretix categories and items to attendee attributes."""

from typing import Any

from app import log
from app.config import CONFIG

# Constants
DEFAULT_ATTRIBUTES_COUNT = 3  # is_remote, is_onsite, online_access


class PretixAttributeMapper:
    """Maps Pretix categories and items to attendee attributes."""

    def __init__(self):
        """Initialize the mapper with configuration."""
        self.config = CONFIG.get("pretix_mapping", {})
        self.category_by_id = self.config.get("categories", {}).get("by_id") or {}
        self.category_by_name = self.config.get("categories", {}).get("by_name") or {}
        self.category_by_ticket_id = self.config.get("categories", {}).get("by_ticket_id") or {}
        self.access_patterns = self.config.get("access_patterns") or {}
        self.attendee_patterns = self.config.get("attendee_patterns") or {}

        # All possible attributes
        self.all_attributes = {
            "is_speaker",
            "is_sponsor",
            "is_organizer",
            "is_volunteer",
            "is_remote",
            "is_keynote",
            "is_onsite",
            "is_guest",
            "online_access",
        }

    def get_attributes_from_item(self, item: dict[str, Any]) -> dict[str, bool]:
        """Get all attributes for an item based on category and name patterns.

        Args:
            item: The Pretix item/product

        Returns:
            Dictionary of attribute names to boolean values
        """
        attributes = {}

        # 1. Category-based mappings
        # set the baseline for on-site and remote access
        category_id = item["category"]
        if category_id and category_id in self.category_by_id:
            attributes.update(self.category_by_id[category_id])
            log.debug(f"Applied category ID mapping for {category_id}: {self.category_by_id[category_id]}")

        # 1. Check for ticket_id mapping
        if item["id"] in self.category_by_ticket_id:
            attributes.update(self.category_by_ticket_id[item["id"]])

        return attributes

    def validate_attribute_coverage(self, items: list[dict[str, Any]], categories: dict[int, dict[str, Any]]) -> dict[str, Any]:
        """Validate which attributes are covered by current configuration.

        Args:
            items: List of all Pretix items
            categories: Dictionary of category ID to category info

        Returns:
            Validation report with coverage statistics
        """
        # Track which attributes are mapped to which items
        attribute_coverage = {attr: [] for attr in self.all_attributes}
        unmapped_items = []

        for item in items:
            # Handle both transformed items and raw items
            item_name = item.get(
                "title", item.get("name", {}).get("en", "Unknown") if isinstance(item.get("name"), dict) else item.get("name", "Unknown")
            )
            category_id = item.get("category_id", item.get("category"))
            category = categories.get(category_id) if category_id else None

            # Get attributes for this item - use stored attributes if available
            attributes = item["_attributes"] if "_attributes" in item else self.get_attributes_from_item(item, category)

            # Track coverage
            has_any_attribute = False
            for attr in self.all_attributes:
                if attributes.get(attr, False):
                    attribute_coverage[attr].append(item_name)
                    has_any_attribute = True

            # Track unmapped items (those with no special attributes)
            if not has_any_attribute or (
                len(attributes) == DEFAULT_ATTRIBUTES_COUNT
                and not attributes.get("is_remote")
                and attributes.get("is_onsite")
                and attributes.get("online_access")
            ):
                unmapped_items.append(item_name)

        # Calculate statistics
        total_items = len(items)
        coverage_stats = {}
        unmapped_attributes = []

        for attr in self.all_attributes:
            count = len(attribute_coverage[attr])
            coverage_stats[attr] = {
                "count": count,
                "items": attribute_coverage[attr],
                "percentage": (count / total_items * 100) if total_items > 0 else 0,
            }
            if count == 0 and attr not in ["is_remote", "is_onsite", "online_access"]:  # Skip access attributes
                unmapped_attributes.append(attr)

        return {
            "total_items": total_items,
            "coverage_stats": coverage_stats,
            "unmapped_attributes": unmapped_attributes,
            "unmapped_items": unmapped_items,
            "categories_found": list(categories.values()),
        }

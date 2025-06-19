"""Shared utilities for ticketing backends."""

from difflib import SequenceMatcher

from app import interface


def fuzzy_match_name(stored_name: str, provided_name: str, exact_threshold: float, close_threshold: float) -> dict:
    """
    Fuzzy name matching with configurable thresholds.

    Args:
        stored_name: Name from the ticketing system
        provided_name: Name provided by the user
        exact_threshold: Ratio above which names are considered a match
        close_threshold: Ratio above which names are considered close

    Returns:
        dict with keys:
        - is_match: bool (matches exactly or above exact_threshold)
        - is_close: bool (above close_threshold but below exact_threshold)
        - hint: str (explanation if not exact match)
        - ratio: float (similarity ratio)
    """
    stored_upper = stored_name.strip().upper()
    provided_upper = provided_name.strip().upper()

    # Exact match
    if stored_upper == provided_upper:
        return {"is_match": True, "is_close": False, "hint": "", "ratio": 1.0}

    # Fuzzy match using normalized names
    ratio = SequenceMatcher(None, interface.normalization(stored_name), interface.normalization(provided_name)).ratio()

    if ratio > exact_threshold:
        return {"is_match": True, "is_close": False, "hint": "", "ratio": ratio}
    elif ratio > close_threshold:
        return {"is_match": False, "is_close": True, "hint": f"Name '{provided_name}' is close but not exact enough", "ratio": ratio}
    else:
        return {"is_match": False, "is_close": False, "hint": f"Could not find '{provided_name}', check spelling", "ratio": ratio}

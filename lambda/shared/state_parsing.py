"""
Parses openFDA distribution_pattern free text into structured state data.
"""

import re

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR", "GU", "VI", "AS", "MP",
}

STATE_NAMES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC", "puerto rico": "PR",
}

CONTIGUOUS_STATES = US_STATES - {"PR", "GU", "VI", "AS", "MP"}


def parse_distribution_pattern(pattern: str) -> dict:
    """
    Parses the openFDA distribution_pattern field into structured state data.

    Examples:
        "Nationwide"
        "FL, MI, MS, and OH."
        "State of California"
        "NY, NJ, CT, PA, and online sales nationwide"
        "Distributed in TX and LA through retail stores"

    Returns:
        {
            "affected_states": ["FL", "MI", "MS", "OH"],
            "is_nationwide": False
        }
    """
    if not pattern:
        return {"affected_states": [], "is_nationwide": False}

    pattern_lower = pattern.lower().strip()

    nationwide_signals = [
        "nationwide", "national distribution", "all states",
        "united states", "throughout the us", "all 50 states",
    ]
    is_nationwide = any(signal in pattern_lower for signal in nationwide_signals)

    affected_states = set()

    if is_nationwide:
        affected_states = set(CONTIGUOUS_STATES)
    else:
        abbrev_matches = re.findall(r"\b([A-Z]{2})\b", pattern)
        for match in abbrev_matches:
            if match in US_STATES:
                affected_states.add(match)

        for name, abbrev in STATE_NAMES.items():
            if name in pattern_lower:
                affected_states.add(abbrev)

    return {
        "affected_states": sorted(affected_states),
        "is_nationwide": is_nationwide,
    }

"""
Recorded OpenRouteService API response fixtures.

These are deterministic sample payloads captured from the ORS API.
Use them in tests to avoid any live network calls and keep the suite
runnable without an ORS_API_KEY.
"""

# ─── Geocode (search) ─────────────────────────────────────────────────────────

GEOCODE_CHICAGO = {
    "features": [
        {
            "geometry": {"coordinates": [-87.6298, 41.8781]},
            "properties": {"label": "Chicago, IL, USA"},
        }
    ]
}

GEOCODE_KANSAS_CITY = {
    "features": [
        {
            "geometry": {"coordinates": [-94.5786, 39.0997]},
            "properties": {"label": "Kansas City, MO, USA"},
        }
    ]
}

GEOCODE_LOS_ANGELES = {
    "features": [
        {
            "geometry": {"coordinates": [-118.2437, 34.0522]},
            "properties": {"label": "Los Angeles, CA, USA"},
        }
    ]
}

GEOCODE_NOT_FOUND = {"features": []}

# ─── Reverse geocode ──────────────────────────────────────────────────────────

REVERSE_GEOCODE_MIDPOINT = {
    "features": [
        {
            "properties": {
                "locality": "Midpoint",
                "region_a": "ST",
                "label": "Midpoint, ST",
            }
        }
    ]
}

# ─── Directions (driving-hgv) ─────────────────────────────────────────────────

ROUTE_CHICAGO_TO_KANSAS_CITY = {
    "features": [
        {
            "properties": {
                "summary": {
                    "distance": 820_000,   # metres  (~510 miles)
                    "duration": 29_520,    # seconds (~8.2 hours)
                }
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-87.63, 41.88],
                    [-91.13, 40.78],
                    [-94.58, 39.10],
                ],
            },
        }
    ]
}

ROUTE_KANSAS_CITY_TO_LOS_ANGELES = {
    "features": [
        {
            "properties": {
                "summary": {
                    "distance": 2_575_000,  # metres  (~1600 miles)
                    "duration": 86_400,     # seconds (24 hours)
                }
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-94.58, 39.10],
                    [-101.84, 35.22],
                    [-110.92, 32.22],
                    [-118.24, 34.05],
                ],
            },
        }
    ]
}

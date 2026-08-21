"""
Geocoder module — wraps OpenRouteService API for geocoding and routing.

Functions:
    geocode(place_name) -> (lat, lon, resolved_name)
    get_route(coords_list) -> {distance_miles, duration_hours, geometry}
    get_intermediate_point(geometry, target_distance_miles) -> (lat, lon, nearest_city)
"""

import logging
import math

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# ORS API base URLs
ORS_BASE_URL = 'https://api.openrouteservice.org'
GEOCODE_URL = f'{ORS_BASE_URL}/geocode/search'
DIRECTIONS_URL = f'{ORS_BASE_URL}/v2/directions/driving-hgv'
REVERSE_GEOCODE_URL = f'{ORS_BASE_URL}/geocode/reverse'

# Simple in-request cache to avoid redundant geocode calls
_geocode_cache = {}


def _get_api_key():
    """Get ORS API key from Django settings."""
    api_key = getattr(settings, 'ORS_API_KEY', '')
    if not api_key:
        raise ValueError(
            "ORS_API_KEY is not configured. "
            "Get a free key at https://openrouteservice.org and add it to your .env file."
        )
    return api_key


def geocode(place_name):
    """
    Convert a place name (city, state or address) to coordinates.

    Args:
        place_name: String like "Chicago, IL" or "123 Main St, Springfield, IL"

    Returns:
        dict: {lat, lon, name} where name is the resolved place name

    Raises:
        ValueError: If the location cannot be found
        requests.RequestException: On API errors
    """
    # Check cache first
    cache_key = place_name.strip().lower()
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]

    api_key = _get_api_key()

    try:
        response = requests.get(
            GEOCODE_URL,
            params={
                'api_key': api_key,
                'text': place_name,
                'size': 1,
                'layers': 'locality,address,venue',
                'boundary.country': 'US',
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error(
            'ORS geocode request failed',
            extra={'place_name': place_name, 'error': str(exc)},
        )
        raise

    data = response.json()
    features = data.get('features', [])

    if not features:
        logger.warning(
            'Geocode returned no results',
            extra={'place_name': place_name},
        )
        raise ValueError(
            f"Could not find location: {place_name!r}. Please check the spelling and try again."
        )

    coords = features[0]['geometry']['coordinates']  # [lon, lat]
    label = features[0]['properties'].get('label', place_name)
    result = {'lat': coords[1], 'lon': coords[0], 'name': label}
    logger.debug(
        'Geocoded location',
        extra={'place_name': place_name, 'resolved': label, 'lat': coords[1], 'lon': coords[0]},
    )
    _geocode_cache[cache_key] = result
    return result


def get_route(coords_list):
    """
    Get driving route between a list of coordinate pairs.

    Uses the driving-hgv (heavy goods vehicle) profile for truck-appropriate routing.

    Args:
        coords_list: List of [lon, lat] pairs, e.g. [[-87.62, 41.87], [-90.19, 38.62]]

    Returns:
        dict: {
            distance_miles: float,
            duration_hours: float,
            geometry: GeoJSON geometry object (for map polyline rendering)
        }

    Raises:
        ValueError: If route cannot be calculated
        requests.RequestException: On API errors
    """
    api_key = _get_api_key()

    response = requests.post(
        f'{DIRECTIONS_URL}/geojson',
        json={
            'coordinates': coords_list,
        },
        headers={
            'Authorization': api_key,
            'Content-Type': 'application/json',
        },
        timeout=30,
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        if response.status_code == 403:
            raise ValueError(
                "ORS API key is invalid or expired. "
                "Get a free key at https://openrouteservice.org and update your .env file."
            )
        # Fallback to returning the raw text
        raise ValueError(f"Routing failed (HTTP {response.status_code}): {response.text}")

    data = response.json()
    features = data.get('features', [])

    if not features:
        raise ValueError("Could not calculate route between the given locations.")

    feature = features[0]
    properties = feature['properties']
    summary = properties.get('summary', {})

    # ORS returns distance in meters, duration in seconds
    distance_meters = summary.get('distance', 0)
    duration_seconds = summary.get('duration', 0)

    return {
        'distance_miles': distance_meters / 1609.344,  # meters to miles
        'duration_hours': duration_seconds / 3600,       # seconds to hours
        'geometry': feature['geometry'],                  # GeoJSON LineString
    }


def get_intermediate_point(geometry, target_distance_miles):
    """
    Find the lat/lon at a specific distance along a route geometry.

    Used to place fuel stops and rest stops at the correct geographic position.

    Args:
        geometry: GeoJSON geometry object with coordinates [[lon, lat], ...]
        target_distance_miles: Distance in miles from the start of the route

    Returns:
        dict: {lat, lon, name} where name is reverse-geocoded nearest city
    """
    coords = geometry.get('coordinates', [])
    if not coords:
        raise ValueError("Route geometry has no coordinates.")

    target_meters = target_distance_miles * 1609.344
    accumulated = 0.0

    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]

        segment_distance = _haversine_meters(lat1, lon1, lat2, lon2)

        if accumulated + segment_distance >= target_meters:
            # Interpolate within this segment
            remaining = target_meters - accumulated
            fraction = remaining / segment_distance if segment_distance > 0 else 0

            interp_lat = lat1 + fraction * (lat2 - lat1)
            interp_lon = lon1 + fraction * (lon2 - lon1)

            # Try to reverse geocode for a city name
            name = _reverse_geocode(interp_lat, interp_lon)

            return {
                'lat': round(interp_lat, 6),
                'lon': round(interp_lon, 6),
                'name': name,
            }

        accumulated += segment_distance

    # If target distance exceeds route length, return the last point
    last_lon, last_lat = coords[-1]
    name = _reverse_geocode(last_lat, last_lon)
    return {
        'lat': round(last_lat, 6),
        'lon': round(last_lon, 6),
        'name': name,
    }


def _haversine_meters(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points in meters."""
    R = 6371000  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def _reverse_geocode(lat, lon):
    """
    Reverse geocode coordinates to get a city name.

    Returns a fallback string if the API call fails.
    """
    try:
        api_key = _get_api_key()
        response = requests.get(
            REVERSE_GEOCODE_URL,
            params={
                'api_key': api_key,
                'point.lat': lat,
                'point.lon': lon,
                'size': 1,
                'layers': 'locality',
            },
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()
        features = data.get('features', [])
        if features:
            props = features[0]['properties']
            city = props.get('locality', props.get('name', ''))
            region = props.get('region_a', props.get('region', ''))
            if city and region:
                return f"{city}, {region}"
            return city or props.get('label', f"({lat:.2f}, {lon:.2f})")
    except Exception:
        pass

    return f"({lat:.2f}, {lon:.2f})"


def clear_cache():
    """Clear the geocode cache. Useful between test runs."""
    global _geocode_cache
    _geocode_cache = {}

"""
Tests for the geocoder module.

All ORS API calls are mocked using the responses library — no real API key needed for testing.
"""

from unittest.mock import patch
import responses
from django.test import TestCase

from trip.geocoder import _haversine_meters, clear_cache, geocode, get_intermediate_point, get_route

# ─── Mock Response Factories ────────────────────────────────────────────────

def _mock_geocode_response(lat, lon, label):
    return {
        'features': [{
            'geometry': {'coordinates': [lon, lat]},
            'properties': {'label': label},
        }]
    }

def _mock_geocode_empty_response():
    return {'features': []}

def _mock_route_response(distance_meters, duration_seconds, coordinates):
    return {
        'features': [{
            'properties': {
                'summary': {
                    'distance': distance_meters,
                    'duration': duration_seconds,
                }
            },
            'geometry': {
                'type': 'LineString',
                'coordinates': coordinates,
            }
        }]
    }

def _mock_reverse_geocode_response(city, region):
    return {
        'features': [{
            'properties': {
                'locality': city,
                'region_a': region,
                'label': f'{city}, {region}',
            }
        }]
    }


# ─── Test Cases ──────────────────────────────────────────────────────────────

@patch('trip.geocoder.settings')
class TestGeocode(TestCase):
    """Tests for the geocode() function."""

    def setUp(self):
        clear_cache()

    @responses.activate
    def test_geocode_chicago(self, mock_settings):
        """Geocoding 'Chicago, IL' returns valid coordinates."""
        mock_settings.ORS_API_KEY = 'test-key'
        responses.add(
            responses.GET,
            'https://api.openrouteservice.org/geocode/search',
            json=_mock_geocode_response(41.8781, -87.6298, 'Chicago, IL, USA'),
            status=200
        )

        result = geocode('Chicago, IL')

        self.assertAlmostEqual(result['lat'], 41.8781, places=3)
        self.assertAlmostEqual(result['lon'], -87.6298, places=3)
        self.assertEqual(result['name'], 'Chicago, IL, USA')

    @responses.activate
    def test_geocode_uses_cache(self, mock_settings):
        """Second call with same name uses cache, doesn't make API call."""
        mock_settings.ORS_API_KEY = 'test-key'
        responses.add(
            responses.GET,
            'https://api.openrouteservice.org/geocode/search',
            json=_mock_geocode_response(41.8781, -87.6298, 'Chicago, IL, USA'),
            status=200
        )

        geocode('Chicago, IL')
        geocode('Chicago, IL')

        # Should only call the API once
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_geocode_not_found_raises(self, mock_settings):
        """Geocoding an unknown location raises ValueError."""
        mock_settings.ORS_API_KEY = 'test-key'
        responses.add(
            responses.GET,
            'https://api.openrouteservice.org/geocode/search',
            json=_mock_geocode_empty_response(),
            status=200
        )

        with self.assertRaises(ValueError) as ctx:
            geocode('Nonexistent Place XYZ')

        self.assertIn("Could not find location", str(ctx.exception))
        self.assertIn("Nonexistent Place XYZ", str(ctx.exception))

    def test_geocode_no_api_key_raises(self, mock_settings):
        """Geocoding without an API key raises ValueError."""
        mock_settings.ORS_API_KEY = ''

        with self.assertRaises(ValueError) as ctx:
            geocode('Chicago, IL')

        self.assertIn("ORS_API_KEY", str(ctx.exception))


@patch('trip.geocoder.settings')
class TestGetRoute(TestCase):
    """Tests for the get_route() function."""

    @responses.activate
    def test_route_returns_distance_and_duration(self, mock_settings):
        """Route between two cities returns positive distance and duration."""
        mock_settings.ORS_API_KEY = 'test-key'

        # ~480 km (298 miles), ~4.5 hours
        responses.add(
            responses.POST,
            'https://api.openrouteservice.org/v2/directions/driving-hgv/geojson',
            json=_mock_route_response(
                distance_meters=480000,
                duration_seconds=16200,
                coordinates=[[-87.63, 41.88], [-89.65, 39.78], [-90.19, 38.63]],
            ),
            status=200
        )

        result = get_route([[-87.63, 41.88], [-90.19, 38.63]])

        self.assertGreater(result['distance_miles'], 0)
        self.assertAlmostEqual(result['distance_miles'], 298.26, places=0)
        self.assertGreater(result['duration_hours'], 0)
        self.assertAlmostEqual(result['duration_hours'], 4.5, places=1)
        self.assertIn('geometry', result)
        self.assertEqual(result['geometry']['type'], 'LineString')

    @responses.activate
    def test_route_long_distance(self, mock_settings):
        """Route for a long trip returns correct mile conversion."""
        mock_settings.ORS_API_KEY = 'test-key'

        # ~2,575 km (1,600 miles)
        responses.add(
            responses.POST,
            'https://api.openrouteservice.org/v2/directions/driving-hgv/geojson',
            json=_mock_route_response(
                distance_meters=2575000,
                duration_seconds=86400,
                coordinates=[[-94.57, 39.09], [-97.33, 37.69], [-101.84, 35.22], [-118.24, 34.05]],
            ),
            status=200
        )

        result = get_route([[-94.57, 39.09], [-118.24, 34.05]])

        self.assertAlmostEqual(result['distance_miles'], 1600, delta=10)
        self.assertAlmostEqual(result['duration_hours'], 24.0, places=1)


@patch('trip.geocoder.settings')
class TestGetIntermediatePoint(TestCase):
    """Tests for the get_intermediate_point() function."""

    @responses.activate
    def test_intermediate_point_at_known_distance(self, mock_settings):
        """Finding a point partway along a route returns valid coordinates."""
        mock_settings.ORS_API_KEY = 'test-key'
        
        responses.add(
            responses.GET,
            'https://api.openrouteservice.org/geocode/reverse',
            json=_mock_reverse_geocode_response('Springfield', 'IL'),
            status=200
        )

        # Create a simple geometry: Chicago → St Louis (roughly straight south)
        # These points are ~300 miles apart
        geometry = {
            'type': 'LineString',
            'coordinates': [
                [-87.63, 41.88],  # Chicago
                [-89.65, 39.78],  # Springfield (midway)
                [-90.19, 38.63],  # St Louis
            ]
        }

        result = get_intermediate_point(geometry, 150)  # 150 miles in

        self.assertIn('lat', result)
        self.assertIn('lon', result)
        self.assertIn('name', result)
        # Should be roughly between Chicago and Springfield
        self.assertGreater(result['lat'], 38.0)
        self.assertLess(result['lat'], 42.0)

    @responses.activate
    def test_intermediate_point_beyond_route(self, mock_settings):
        """If target distance exceeds route, returns the last point."""
        mock_settings.ORS_API_KEY = 'test-key'
        
        responses.add(
            responses.GET,
            'https://api.openrouteservice.org/geocode/reverse',
            json=_mock_reverse_geocode_response('St Louis', 'MO'),
            status=200
        )

        geometry = {
            'type': 'LineString',
            'coordinates': [
                [-87.63, 41.88],
                [-90.19, 38.63],
            ]
        }

        result = get_intermediate_point(geometry, 99999)  # Way beyond route

        # Should return the last point (St Louis)
        self.assertAlmostEqual(result['lat'], 38.63, places=1)
        self.assertAlmostEqual(result['lon'], -90.19, places=1)

    def test_intermediate_point_empty_geometry_raises(self, mock_settings):
        """Empty geometry raises ValueError."""
        mock_settings.ORS_API_KEY = 'test-key'

        with self.assertRaises(ValueError):
            get_intermediate_point({'coordinates': []}, 100)


class TestHaversine(TestCase):
    """Tests for the haversine distance calculation."""

    def test_chicago_to_springfield(self):
        """Distance from Chicago to Springfield IL is roughly 185 miles (298 km)."""
        distance = _haversine_meters(41.88, -87.63, 39.78, -89.65)
        distance_miles = distance / 1609.344
        # Should be roughly 185 miles (great circle)
        self.assertAlmostEqual(distance_miles, 185, delta=20)

    def test_same_point_is_zero(self):
        """Distance from a point to itself is zero."""
        distance = _haversine_meters(41.88, -87.63, 41.88, -87.63)
        self.assertAlmostEqual(distance, 0, places=1)

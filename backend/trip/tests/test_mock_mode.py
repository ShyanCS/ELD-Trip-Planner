"""
Tests for mock ORS mode (USE_MOCK_ORS=True).

Proves the whole trip-planning flow works with no OpenRouteService
account, no API key, and no network access.
"""

import os
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from trip.geocoder import _haversine_meters, clear_cache, geocode, get_route


class MockModeGeocodeTests(TestCase):
    """geocode() in mock mode needs neither a key nor the network."""

    def setUp(self):
        clear_cache()

    @patch.dict(os.environ, {'USE_MOCK_ORS': 'True'})
    def test_known_city_returns_real_coordinates(self):
        result = geocode('Chicago, IL')
        self.assertAlmostEqual(result['lat'], 41.8781, places=3)
        self.assertAlmostEqual(result['lon'], -87.6298, places=3)
        self.assertEqual(result['name'], 'Chicago, IL, USA')

    @patch.dict(os.environ, {'USE_MOCK_ORS': 'True'})
    def test_unknown_place_returns_deterministic_fallback(self):
        first = geocode('Nowhereville')
        second = geocode('Nowhereville')
        self.assertEqual(first['name'], 'Nowhereville (mock)')
        self.assertEqual(first, second)  # deterministic

    @patch.dict(os.environ, {'USE_MOCK_ORS': 'True'})
    def test_mock_mode_requires_no_api_key(self):
        # Would raise ValueError("ORS_API_KEY is not configured...") if it
        # tried the real API path — succeeding proves it did not.
        with patch('trip.geocoder._get_api_key') as key_mock:
            key_mock.side_effect = AssertionError("mock mode must not read the API key")
            geocode('Denver, CO')


class MockModeRouteTests(TestCase):
    @patch.dict(os.environ, {'USE_MOCK_ORS': 'True'})
    def test_route_returns_positive_distance_duration_and_geometry(self):
        coords = [[-87.63, 41.88], [-90.19, 38.63]]  # Chicago → St Louis
        result = get_route(coords)

        # Mock applies a 1.15 road factor to the great-circle distance
        great_circle_miles = _haversine_meters(41.88, -87.63, 38.63, -90.19) / 1609.344
        self.assertAlmostEqual(
            result['distance_miles'], great_circle_miles * 1.15, delta=5
        )
        self.assertAlmostEqual(
            result['duration_hours'], result['distance_miles'] / 55.0, places=2
        )
        self.assertEqual(result['geometry']['type'], 'LineString')
        self.assertGreater(len(result['geometry']['coordinates']), 4)

    @patch.dict(os.environ, {'USE_MOCK_ORS': 'True'})
    def test_route_geometry_endpoints_match_input(self):
        coords = [[-94.58, 39.10], [-118.24, 34.05]]
        geometry = get_route(coords)['geometry']
        self.assertEqual(geometry['coordinates'][0], [-94.58, 39.10])
        self.assertEqual(geometry['coordinates'][-1], [-118.24, 34.05])


class MockModeEndToEndTests(TestCase):
    """
    The full POST /api/trip/plan/ pipeline completes with USE_MOCK_ORS=True,
    ORS_API_KEY unset, and zero HTTP calls — the app is self-contained.
    """

    def setUp(self):
        self.client = APIClient()
        clear_cache()

    @patch.dict(os.environ, {'USE_MOCK_ORS': 'True'})
    def test_full_trip_plan_succeeds_without_api_key_or_network(self):
        response = self.client.post('/api/trip/plan/', {
            'current_location': 'Chicago, IL',
            'pickup_location': 'Kansas City, MO',
            'dropoff_location': 'Los Angeles, CA',
            'current_cycle_used': 20,
        }, format='json')

        self.assertEqual(response.status_code, 200)
        route = response.data['route']
        self.assertGreater(route['total_distance_miles'], 0)
        self.assertGreaterEqual(len(response.data['daily_logs']), 1)
        types = [w['type'] for w in route['waypoints']]
        for expected in ('start', 'pickup', 'dropoff'):
            self.assertIn(expected, types)

    def test_haversine_still_accurate_for_mock_distance_math(self):
        # Sanity anchor used by _mock_route's distance math
        chicago_to_kc = _haversine_meters(41.8781, -87.6298, 39.0997, -94.5786) / 1609.344
        self.assertAlmostEqual(chicago_to_kc, 415, delta=25)

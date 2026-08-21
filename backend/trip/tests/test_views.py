"""
Tests for the TripPlanView API endpoint.

All ORS API calls are mocked — no real API key needed.
Tests verify the full pipeline: validation → geocoding → routing → HOS → response.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.test import APIClient

# ─── Mock Response Factories ────────────────────────────────────────────────

def _mock_geocode_responses():
    """
    Returns a side_effect function for requests.get that serves geocode
    and reverse-geocode responses based on the URL params.
    """
    geocode_db = {
        'chicago': (41.8781, -87.6298, 'Chicago, IL, USA'),
        'kansas city': (39.0997, -94.5786, 'Kansas City, MO, USA'),
        'los angeles': (34.0522, -118.2437, 'Los Angeles, CA, USA'),
    }

    def side_effect(url, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()

        params = kwargs.get('params', {})

        if '/geocode/search' in url:
            text = params.get('text', '').lower()
            for key, (lat, lon, label) in geocode_db.items():
                if key in text:
                    mock_resp.json.return_value = {
                        'features': [{
                            'geometry': {'coordinates': [lon, lat]},
                            'properties': {'label': label},
                        }]
                    }
                    return mock_resp

            # Unknown location
            mock_resp.json.return_value = {'features': []}
            return mock_resp

        elif '/geocode/reverse' in url:
            mock_resp.json.return_value = {
                'features': [{
                    'properties': {
                        'locality': 'SomeCity',
                        'region_a': 'ST',
                        'label': 'SomeCity, ST',
                    }
                }]
            }
            return mock_resp

        return mock_resp

    return side_effect


def _mock_route_response(distance_meters, duration_seconds, coords):
    """Create a mock route response for requests.post."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        'features': [{
            'properties': {
                'summary': {
                    'distance': distance_meters,
                    'duration': duration_seconds,
                }
            },
            'geometry': {
                'type': 'LineString',
                'coordinates': coords,
            }
        }]
    }
    return mock_resp


def _mock_route_side_effect():
    """
    Returns a side_effect for requests.post that returns different routes
    based on the coordinates in the request body.
    """
    call_count = [0]

    def side_effect(url, **kwargs):
        call_count[0] += 1

        if call_count[0] == 1:
            # Route 1: Current → Pickup (~510 miles)
            return _mock_route_response(
                distance_meters=820000,   # ~510 miles
                duration_seconds=29520,   # ~8.2 hours
                coords=[
                    [-87.63, 41.88],
                    [-91.13, 40.78],
                    [-94.58, 39.10],
                ],
            )
        else:
            # Route 2: Pickup → Dropoff (~1600 miles)
            return _mock_route_response(
                distance_meters=2575000,  # ~1600 miles
                duration_seconds=86400,   # ~24 hours
                coords=[
                    [-94.58, 39.10],
                    [-101.84, 35.22],
                    [-110.92, 32.22],
                    [-118.24, 34.05],
                ],
            )

    return side_effect


# ─── Test Cases ──────────────────────────────────────────────────────────────

class TestVersionView(TestCase):
    """Tests for GET /api/version/."""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/trip/version/'

    def test_returns_200(self):
        """Version endpoint returns HTTP 200."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_response_has_required_keys(self):
        """Response includes app, version, django_version, python_version."""
        response = self.client.get(self.url)
        data = response.data
        for key in ('app', 'version', 'django_version', 'python_version'):
            self.assertIn(key, data)

    def test_app_name(self):
        """App name is eld-trip-planner."""
        response = self.client.get(self.url)
        self.assertEqual(response.data['app'], 'eld-trip-planner')


class TestMetricsView(TestCase):
    """Tests for GET /api/metrics/."""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/trip/metrics/'

    def test_returns_200(self):
        """Metrics endpoint returns HTTP 200."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_response_has_required_keys(self):
        """Response includes status, version, uptime_seconds, requests_total."""
        response = self.client.get(self.url)
        for key in ('status', 'version', 'uptime_seconds', 'requests_total'):
            self.assertIn(key, response.data)

    def test_uptime_is_positive(self):
        """Uptime must be a non-negative number."""
        response = self.client.get(self.url)
        self.assertGreaterEqual(response.data['uptime_seconds'], 0)


@patch('trip.geocoder.settings')
class TestTripPlanViewValidation(TestCase):
    """Tests for input validation in the API endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/trip/plan/'

    def test_empty_body_returns_400(self, mock_settings):
        """POST with empty body returns 400 with validation errors."""
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('details', response.data)

    def test_missing_field_returns_400(self, mock_settings):
        """POST with missing required field returns 400."""
        response = self.client.post(self.url, {
            'current_location': 'Chicago, IL',
            'pickup_location': 'Kansas City, MO',
            # Missing dropoff_location and current_cycle_used
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_cycle_over_70_returns_400(self, mock_settings):
        """Cycle hours > 70 should be rejected."""
        response = self.client.post(self.url, {
            'current_location': 'Chicago, IL',
            'pickup_location': 'Kansas City, MO',
            'dropoff_location': 'Los Angeles, CA',
            'current_cycle_used': 75,
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_negative_cycle_returns_400(self, mock_settings):
        """Negative cycle hours should be rejected."""
        response = self.client.post(self.url, {
            'current_location': 'Chicago, IL',
            'pickup_location': 'Kansas City, MO',
            'dropoff_location': 'Los Angeles, CA',
            'current_cycle_used': -5,
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_invalid_location_chars_returns_400(self, mock_settings):
        """Location with script injection characters is rejected by RegexValidator."""
        response = self.client.post(self.url, {
            'current_location': '<script>alert(1)</script>',
            'pickup_location': 'Kansas City, MO',
            'dropoff_location': 'Los Angeles, CA',
            'current_cycle_used': 10,
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_same_pickup_and_dropoff_returns_400(self, mock_settings):
        """Pickup and dropoff at the same location is rejected by cross-field validate()."""
        response = self.client.post(self.url, {
            'current_location': 'Chicago, IL',
            'pickup_location': 'Kansas City, MO',
            'dropoff_location': 'Kansas City, MO',
            'current_cycle_used': 10,
        }, format='json')
        self.assertEqual(response.status_code, 400)


@patch('trip.geocoder.settings')
class TestTripPlanViewSuccess(TestCase):
    """Tests for successful trip planning with mocked ORS API."""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/trip/plan/'

    @patch('trip.geocoder.requests.post')
    @patch('trip.geocoder.requests.get')
    def test_valid_trip_returns_200(self, mock_get, mock_post, mock_settings):
        """Valid trip request returns 200 with expected structure."""
        mock_settings.ORS_API_KEY = 'test-key'
        mock_get.side_effect = _mock_geocode_responses()
        mock_post.side_effect = _mock_route_side_effect()

        response = self.client.post(self.url, {
            'current_location': 'Chicago, IL',
            'pickup_location': 'Kansas City, MO',
            'dropoff_location': 'Los Angeles, CA',
            'current_cycle_used': 20,
        }, format='json')

        self.assertEqual(response.status_code, 200)

    @patch('trip.geocoder.requests.post')
    @patch('trip.geocoder.requests.get')
    def test_response_has_route(self, mock_get, mock_post, mock_settings):
        """Response contains route object with distance, duration, geometry."""
        mock_settings.ORS_API_KEY = 'test-key'
        mock_get.side_effect = _mock_geocode_responses()
        mock_post.side_effect = _mock_route_side_effect()

        response = self.client.post(self.url, {
            'current_location': 'Chicago, IL',
            'pickup_location': 'Kansas City, MO',
            'dropoff_location': 'Los Angeles, CA',
            'current_cycle_used': 20,
        }, format='json')

        route = response.data['route']
        self.assertIn('total_distance_miles', route)
        self.assertIn('total_duration_hours', route)
        self.assertIn('geometry', route)
        self.assertIn('waypoints', route)
        self.assertGreater(route['total_distance_miles'], 0)

    @patch('trip.geocoder.requests.post')
    @patch('trip.geocoder.requests.get')
    def test_response_has_daily_logs(self, mock_get, mock_post, mock_settings):
        """Response contains daily_logs array with correct structure."""
        mock_settings.ORS_API_KEY = 'test-key'
        mock_get.side_effect = _mock_geocode_responses()
        mock_post.side_effect = _mock_route_side_effect()

        response = self.client.post(self.url, {
            'current_location': 'Chicago, IL',
            'pickup_location': 'Kansas City, MO',
            'dropoff_location': 'Los Angeles, CA',
            'current_cycle_used': 20,
        }, format='json')

        logs = response.data['daily_logs']
        self.assertGreater(len(logs), 0)

        # Check first day structure
        day1 = logs[0]
        self.assertIn('day', day1)
        self.assertIn('date', day1)
        self.assertIn('events', day1)
        self.assertIn('totals', day1)
        self.assertIn('miles_today', day1)
        self.assertIn('remarks', day1)

    @patch('trip.geocoder.requests.post')
    @patch('trip.geocoder.requests.get')
    def test_daily_logs_sum_to_24(self, mock_get, mock_post, mock_settings):
        """Every daily log totals sum to 24.0."""
        mock_settings.ORS_API_KEY = 'test-key'
        mock_get.side_effect = _mock_geocode_responses()
        mock_post.side_effect = _mock_route_side_effect()

        response = self.client.post(self.url, {
            'current_location': 'Chicago, IL',
            'pickup_location': 'Kansas City, MO',
            'dropoff_location': 'Los Angeles, CA',
            'current_cycle_used': 20,
        }, format='json')

        for log in response.data['daily_logs']:
            total = sum(log['totals'].values())
            self.assertAlmostEqual(total, 24.0, places=1,
                                   msg=f"Day {log['day']} totals sum to {total}")

    @patch('trip.geocoder.requests.post')
    @patch('trip.geocoder.requests.get')
    def test_waypoints_include_required_types(self, mock_get, mock_post, mock_settings):
        """Waypoints should include at least start, pickup, and dropoff."""
        mock_settings.ORS_API_KEY = 'test-key'
        mock_get.side_effect = _mock_geocode_responses()
        mock_post.side_effect = _mock_route_side_effect()

        response = self.client.post(self.url, {
            'current_location': 'Chicago, IL',
            'pickup_location': 'Kansas City, MO',
            'dropoff_location': 'Los Angeles, CA',
            'current_cycle_used': 20,
        }, format='json')

        waypoints = response.data['route']['waypoints']
        types = [w['type'] for w in waypoints]

        self.assertIn('start', types)
        self.assertIn('pickup', types)
        self.assertIn('dropoff', types)

    @patch('trip.geocoder.requests.post')
    @patch('trip.geocoder.requests.get')
    def test_merged_geometry(self, mock_get, mock_post, mock_settings):
        """Route geometry should be a merged LineString."""
        mock_settings.ORS_API_KEY = 'test-key'
        mock_get.side_effect = _mock_geocode_responses()
        mock_post.side_effect = _mock_route_side_effect()

        response = self.client.post(self.url, {
            'current_location': 'Chicago, IL',
            'pickup_location': 'Kansas City, MO',
            'dropoff_location': 'Los Angeles, CA',
            'current_cycle_used': 20,
        }, format='json')

        geom = response.data['route']['geometry']
        self.assertEqual(geom['type'], 'LineString')
        # Merged: 3 points + (4 - 1 duplicate) = 6 points
        self.assertEqual(len(geom['coordinates']), 6)


@patch('trip.geocoder.settings')
class TestTripPlanViewErrors(TestCase):
    """Tests for error handling in the API endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/trip/plan/'

    @patch('trip.geocoder.requests.get')
    def test_unknown_location_returns_400(self, mock_get, mock_settings):
        """Unknown location geocode failure returns 400."""
        mock_settings.ORS_API_KEY = 'test-key'
        mock_get.side_effect = _mock_geocode_responses()

        response = self.client.post(self.url, {
            'current_location': 'Nonexistent Place XYZ',
            'pickup_location': 'Kansas City, MO',
            'dropoff_location': 'Los Angeles, CA',
            'current_cycle_used': 20,
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    def test_no_api_key_returns_400(self, mock_settings):
        """Missing API key returns 400."""
        mock_settings.ORS_API_KEY = ''

        response = self.client.post(self.url, {
            'current_location': 'Chicago, IL',
            'pickup_location': 'Kansas City, MO',
            'dropoff_location': 'Los Angeles, CA',
            'current_cycle_used': 20,
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

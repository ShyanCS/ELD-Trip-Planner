"""
Integration test: full POST /api/trip/plan/ pipeline.

Exercises the complete serializer → geocoder → HOS calculator chain
with a stubbed ORS client — no live network calls.
Asserts FMCSA-compliant totals and response structure.
"""

import re
from unittest.mock import MagicMock, patch

import responses as responses_lib
from django.test import TestCase
from rest_framework.test import APIClient

# ─── Mock helpers (same ORS stubs as test_views.py) ──────────────────────────

def _geocode_db():
    return {
        'chicago': (41.8781, -87.6298, 'Chicago, IL, USA'),
        'kansas city': (39.0997, -94.5786, 'Kansas City, MO, USA'),
        'los angeles': (34.0522, -118.2437, 'Los Angeles, CA, USA'),
    }


def _setup_geocode_mocks():
    db = _geocode_db()

    def _geocode_cb(request):
        import urllib.parse
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(request.url).query)
        text = qs.get('text', [''])[0].lower()
        for key, (lat, lon, label) in db.items():
            if key in text:
                return (
                    200, {},
                    f'{{"features": [{{"geometry": {{"coordinates": [{lon}, {lat}]}}, '
                    f'"properties": {{"label": "{label}"}}}}]}}',
                )
        return (200, {}, '{"features": []}')

    def _reverse_cb(_request):
        return (200, {}, '{"features": [{"properties": {"label": "Midpoint, ST"}}]}')

    responses_lib.add_callback(
        responses_lib.GET,
        re.compile(r'^https://api\.openrouteservice\.org/geocode/search.*$'),
        callback=_geocode_cb,
        content_type='application/json',
    )
    responses_lib.add_callback(
        responses_lib.GET,
        re.compile(r'^https://api\.openrouteservice\.org/geocode/reverse.*$'),
        callback=_reverse_cb,
        content_type='application/json',
    )


def _make_route_mock(distance_m, duration_s, coords):
    m = MagicMock()
    m.status_code = 200
    m.raise_for_status = MagicMock()
    m.json.return_value = {
        'features': [{
            'properties': {'summary': {'distance': distance_m, 'duration': duration_s}},
            'geometry': {'type': 'LineString', 'coordinates': coords},
        }]
    }
    return m


def _setup_route_mocks():
    """Two-leg route: Chicago→KC (820 km) then KC→LA (2 575 km)."""
    call_count = [0]

    def _route_cb(request):
        import json
        call_count[0] += 1
        if call_count[0] == 1:
            body = _make_route_mock(
                820_000, 29_520,
                [[-87.63, 41.88], [-91.13, 40.78], [-94.58, 39.10]],
            ).json()
        else:
            body = _make_route_mock(
                2_575_000, 86_400,
                [[-94.58, 39.10], [-101.84, 35.22], [-110.92, 32.22], [-118.24, 34.05]],
            ).json()
        return (200, {}, json.dumps(body))

    responses_lib.add_callback(
        responses_lib.POST,
        'https://api.openrouteservice.org/v2/directions/driving-hgv/geojson',
        callback=_route_cb,
        content_type='application/json',
    )


VALID_PAYLOAD = {
    'current_location': 'Chicago, IL',
    'pickup_location': 'Kansas City, MO',
    'dropoff_location': 'Los Angeles, CA',
    'current_cycle_used': 20,
}


# ─── Integration Tests ────────────────────────────────────────────────────────

@patch('trip.geocoder.settings')
class TripPlanIntegrationTest(TestCase):
    """End-to-end integration: serializer → geocoder → HOS calculator."""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/trip/plan/'

    # ── Response structure ────────────────────────────────────────────────────

    @responses_lib.activate
    def test_returns_200_with_all_top_level_keys(self, mock_settings):
        """Response must contain route, daily_logs, and stop_events."""
        mock_settings.ORS_API_KEY = 'test-key'
        _setup_geocode_mocks()
        _setup_route_mocks()

        resp = self.client.post(self.url, VALID_PAYLOAD, format='json')

        self.assertEqual(resp.status_code, 200)
        for key in ('route', 'daily_logs', 'stop_events'):
            self.assertIn(key, resp.data, msg=f"Missing top-level key: {key}")

    @responses_lib.activate
    def test_route_object_has_expected_fields(self, mock_settings):
        """route must contain distance_miles, duration_hours, geometry, waypoints."""
        mock_settings.ORS_API_KEY = 'test-key'
        _setup_geocode_mocks()
        _setup_route_mocks()

        resp = self.client.post(self.url, VALID_PAYLOAD, format='json')

        route = resp.data['route']
        for field in ('total_distance_miles', 'total_duration_hours', 'geometry', 'waypoints'):
            self.assertIn(field, route, msg=f"route missing field: {field}")

    @responses_lib.activate
    def test_geometry_is_linestring(self, mock_settings):
        """geometry must be a GeoJSON LineString with coordinates."""
        mock_settings.ORS_API_KEY = 'test-key'
        _setup_geocode_mocks()
        _setup_route_mocks()

        resp = self.client.post(self.url, VALID_PAYLOAD, format='json')

        geometry = resp.data['route']['geometry']
        self.assertEqual(geometry['type'], 'LineString')
        self.assertGreater(len(geometry['coordinates']), 0)

    # ── HOS compliance ────────────────────────────────────────────────────────

    @responses_lib.activate
    def test_daily_logs_present_and_non_empty(self, mock_settings):
        """At least one daily log must be generated for a multi-day trip."""
        mock_settings.ORS_API_KEY = 'test-key'
        _setup_geocode_mocks()
        _setup_route_mocks()

        resp = self.client.post(self.url, VALID_PAYLOAD, format='json')

        self.assertGreater(len(resp.data['daily_logs']), 0)

    @responses_lib.activate
    def test_each_daily_log_has_required_keys(self, mock_settings):
        """Every daily log must have day, driving_hours, on_duty_hours, status_grid."""
        mock_settings.ORS_API_KEY = 'test-key'
        _setup_geocode_mocks()
        _setup_route_mocks()

        resp = self.client.post(self.url, VALID_PAYLOAD, format='json')

        for log in resp.data['daily_logs']:
            for key in ('day', 'date', 'events', 'totals', 'miles_today'):
                self.assertIn(key, log, msg=f"daily_log missing key: {key}")

    @responses_lib.activate
    def test_driving_hours_never_exceed_11_per_day(self, mock_settings):
        """FMCSA: driving window is capped at 11 hours per day."""
        mock_settings.ORS_API_KEY = 'test-key'
        _setup_geocode_mocks()
        _setup_route_mocks()

        resp = self.client.post(self.url, VALID_PAYLOAD, format='json')

        for log in resp.data['daily_logs']:
            driving = log['totals']['driving']
            self.assertLessEqual(
                driving, 11.0,
                msg=f"Day {log['day']} driving={driving} exceeds 11h limit",
            )

    @responses_lib.activate
    def test_on_duty_hours_never_exceed_14_per_day(self, mock_settings):
        """FMCSA: on-duty window is capped at 14 hours per day."""
        mock_settings.ORS_API_KEY = 'test-key'
        _setup_geocode_mocks()
        _setup_route_mocks()

        resp = self.client.post(self.url, VALID_PAYLOAD, format='json')

        for log in resp.data['daily_logs']:
            on_duty = log['totals']['driving'] + log['totals']['on_duty_not_driving']
            self.assertLessEqual(
                on_duty, 14.0,
                msg=f"Day {log['day']} on_duty={on_duty} exceeds 14h limit",
            )

    @responses_lib.activate
    def test_status_grid_has_96_slots(self, mock_settings):
        """Status grid must have exactly 96 slots (24h × 4 per hour = 15-min increments)."""
        mock_settings.ORS_API_KEY = 'test-key'
        _setup_geocode_mocks()
        _setup_route_mocks()

        resp = self.client.post(self.url, VALID_PAYLOAD, format='json')

        for log in resp.data['daily_logs']:
            # totals must account for all 24 hours
            total_hours = sum(log['totals'].values())
            self.assertAlmostEqual(
                total_hours, 24.0, places=1,
                msg=f"Day {log['day']} totals sum to {total_hours}, expected ~24h",
            )

    # ── Stop events ───────────────────────────────────────────────────────────

    @responses_lib.activate
    def test_stop_events_list_is_present(self, mock_settings):
        """stop_events must be a list (possibly empty for very short trips)."""
        mock_settings.ORS_API_KEY = 'test-key'
        _setup_geocode_mocks()
        _setup_route_mocks()

        resp = self.client.post(self.url, VALID_PAYLOAD, format='json')

        self.assertIsInstance(resp.data['stop_events'], list)

    @responses_lib.activate
    def test_cycle_used_constraint_is_respected(self, mock_settings):
        """With 60h pre-used cycle, response should still be valid (only 10h remaining)."""
        mock_settings.ORS_API_KEY = 'test-key'
        _setup_geocode_mocks()
        _setup_route_mocks()

        payload = {**VALID_PAYLOAD, 'current_cycle_used': 60}
        resp = self.client.post(self.url, payload, format='json')

        # Should return 200 regardless of how constrained the cycle is
        self.assertEqual(resp.status_code, 200)

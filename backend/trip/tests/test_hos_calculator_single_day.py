"""
Tests for the HOS Calculator — single-day scenarios.

Covers:
    - TestHelpers: helper function unit tests
    - TestShortTrip: 200-mile trip completing in a single day
    - TestHoursSumTo24: all day totals sum to exactly 24.0 hours
"""

from django.test import TestCase
from trip.hos_calculator import calculate_trip, _hours_to_time_str


class TestHelpers(TestCase):
    """Test helper functions."""

    def test_hours_to_time_str(self):
        """Decimal hours convert to HH:MM correctly."""
        self.assertEqual(_hours_to_time_str(0.0), '00:00')
        self.assertEqual(_hours_to_time_str(8.0), '08:00')
        self.assertEqual(_hours_to_time_str(8.5), '08:30')
        self.assertEqual(_hours_to_time_str(13.25), '13:15')
        self.assertEqual(_hours_to_time_str(23.75), '23:45')
        self.assertEqual(_hours_to_time_str(12.0), '12:00')


class TestShortTrip(TestCase):
    """
    Test 1: Short trip — 200 miles, cycle=0.
    Should complete in a single day with no rest breaks or fuel stops.

    For this test we use: Current → Pickup = 100mi, Pickup → Dropoff = 100mi
    """

    def setUp(self):
        self.segments = [
            {
                'distance_miles': 100,
                'from_location': 'City A',
                'to_location': 'City B',
            },
            {
                'distance_miles': 100,
                'from_location': 'City B',
                'to_location': 'City C',
            },
        ]
        self.result = calculate_trip(
            segments=self.segments,
            current_cycle_used=0,
            start_date='2026-05-07',
        )

    def test_single_day_log(self):
        """A 200-mile trip should produce exactly 1 daily log."""
        self.assertEqual(len(self.result['daily_logs']), 1)

    def test_day_date(self):
        """Day 1 date should match start_date."""
        self.assertEqual(self.result['daily_logs'][0]['date'], '2026-05-07')

    def test_day_number(self):
        """Day number should be 1."""
        self.assertEqual(self.result['daily_logs'][0]['day'], 1)

    def test_has_pre_trip_inspection(self):
        """First event should be pre-trip inspection (OND, 0.5 hrs)."""
        events = self.result['daily_logs'][0]['events']
        first = events[0]
        self.assertEqual(first['status'], 'on_duty_not_driving')
        self.assertAlmostEqual(first['hours'], 0.5, places=2)
        self.assertEqual(first['time'], '08:00')

    def test_has_driving_events(self):
        """There should be at least one driving event."""
        events = self.result['daily_logs'][0]['events']
        driving = [e for e in events if e['status'] == 'driving']
        self.assertGreater(len(driving), 0)

    def test_has_pickup_stop(self):
        """There should be a 1-hour OND event for pickup."""
        events = self.result['daily_logs'][0]['events']
        ond_events = [e for e in events if e['status'] == 'on_duty_not_driving']
        ond_hours = [round(e['hours'], 1) for e in ond_events]
        self.assertIn(1.0, ond_hours)

    def test_has_dropoff_stop(self):
        """There should be dropoff + post-trip inspection events."""
        events = self.result['daily_logs'][0]['events']
        ond_events = [e for e in events if e['status'] == 'on_duty_not_driving']
        # Pre-trip (0.5) + pickup (1.0) + dropoff (1.0) + post-trip (0.5) = 3.0 total OND
        total_ond = sum(e['hours'] for e in ond_events)
        self.assertAlmostEqual(total_ond, 3.0, places=1)

    def test_total_driving_miles(self):
        """Total driving miles should equal 200."""
        log = self.result['daily_logs'][0]
        self.assertAlmostEqual(log['miles_today'], 200, delta=1)

    def test_no_stop_events(self):
        """Short trip should have no fuel or rest stops."""
        self.assertEqual(len(self.result['stop_events']), 0)

    def test_remarks_present(self):
        """Remarks list should have entries."""
        remarks = self.result['daily_logs'][0]['remarks']
        self.assertGreater(len(remarks), 0)
        self.assertTrue(any('Pre-trip' in r for r in remarks))


class TestHoursSumTo24(TestCase):
    """
    Test 7: Every DailyLog totals must sum to exactly 24.0 hours.

    Tests multiple trip lengths to ensure padding always works correctly.
    """

    def _assert_totals_sum_to_24(self, daily_logs):
        """Helper: assert all daily logs sum to 24."""
        for log in daily_logs:
            total = sum(log['totals'].values())
            self.assertAlmostEqual(
                total, 24.0, places=1,
                msg=f"Day {log['day']} totals sum to {total}, not 24.0. Totals: {log['totals']}"
            )

    def test_short_trip_sums_to_24(self):
        """200-mile trip: day totals sum to 24."""
        result = calculate_trip(
            segments=[
                {'distance_miles': 100, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 100, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )
        self._assert_totals_sum_to_24(result['daily_logs'])

    def test_medium_trip_sums_to_24(self):
        """510-mile trip: day totals sum to 24."""
        result = calculate_trip(
            segments=[
                {'distance_miles': 300, 'from_location': 'Chicago', 'to_location': 'Kansas City'},
                {'distance_miles': 210, 'from_location': 'Kansas City', 'to_location': 'Tulsa'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )
        self._assert_totals_sum_to_24(result['daily_logs'])

    def test_exactly_11_hours_driving_sums_to_24(self):
        """605-mile trip (exactly 11 hours at 55mph): day totals sum to 24."""
        result = calculate_trip(
            segments=[
                {'distance_miles': 300, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 305, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )
        self._assert_totals_sum_to_24(result['daily_logs'])

    def test_multi_day_trip_sums_to_24(self):
        """1000-mile trip spanning 2+ days: every day sums to 24."""
        result = calculate_trip(
            segments=[
                {'distance_miles': 400, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 600, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )
        self._assert_totals_sum_to_24(result['daily_logs'])
        self.assertGreaterEqual(len(result['daily_logs']), 2)

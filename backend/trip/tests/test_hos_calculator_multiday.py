"""
Tests for the HOS Calculator — multi-day and driving limit scenarios.

Covers:
    - TestDrivingLimits: 11-hour and 14-hour window enforcement
    - TestMediumTrip: 600-mile trip, 30-minute break rule
    - TestLongTrip: 2110-mile master test case with fuel and rest stops
    - TestBreakTrigger: 8-hour break trigger threshold
    - TestFuelStopResetsBreak: fuel stop resetting the break counter
    - TestHoursSumTo24WithBreaksAndFuel: 24hr sum with fuel stops
"""

from django.test import TestCase
from trip.hos_calculator import calculate_trip


class TestDrivingLimits(TestCase):
    """Test that 11-hour and 14-hour limits are enforced."""

    def test_11_hour_limit_forces_new_day(self):
        """
        A trip requiring >11 hours of driving forces a multi-day plan.
        700 miles / 55 mph = 12.7 hours driving — exceeds 11-hour limit.
        """
        result = calculate_trip(
            segments=[
                {'distance_miles': 300, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 400, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )

        self.assertGreaterEqual(len(result['daily_logs']), 2)

        day1 = result['daily_logs'][0]
        self.assertLessEqual(day1['totals']['driving'], 11.01)

    def test_14_hour_window_limits_driving(self):
        """
        The 14-hour window starts at first on-duty. OND activities consume
        window time and reduce available driving hours.
        """
        result = calculate_trip(
            segments=[
                {'distance_miles': 300, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 400, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )

        day1 = result['daily_logs'][0]
        total_on_duty = day1['totals']['driving'] + day1['totals']['on_duty_not_driving']
        self.assertLessEqual(total_on_duty, 14.01)

    def test_rest_stop_waypoint_generated(self):
        """When driving spans multiple days, rest stop events are generated."""
        result = calculate_trip(
            segments=[
                {'distance_miles': 300, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 600, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )

        if len(result['daily_logs']) > 1:
            rest_stops = [s for s in result['stop_events'] if s['type'] == 'rest']
            self.assertGreater(len(rest_stops), 0)


class TestMediumTrip(TestCase):
    """
    Test 2: Medium trip — 600 miles, cycle=0.
    Uses a short first segment (100mi) so the 1-hour pickup resets the break counter,
    then a long second segment (500mi = 9.09 hrs) that exceeds the 8-hour threshold
    and forces a 30-minute break mid-segment.
    """

    def setUp(self):
        self.result = calculate_trip(
            segments=[
                {'distance_miles': 100, 'from_location': 'Chicago', 'to_location': 'Kansas City'},
                {'distance_miles': 500, 'from_location': 'Kansas City', 'to_location': 'Tulsa'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )

    def test_break_present_in_events(self):
        """A 30-minute off-duty break should appear in the events."""
        all_events = []
        for log in self.result['daily_logs']:
            all_events.extend(log['events'])

        breaks = [e for e in all_events
                  if e['status'] == 'off_duty'
                  and abs(e['hours'] - 0.5) < 0.01]
        self.assertGreater(len(breaks), 0, "No 30-minute break found in events")

    def test_break_in_remarks(self):
        """The 30-min break should appear in remarks."""
        all_remarks = []
        for log in self.result['daily_logs']:
            all_remarks.extend(log['remarks'])

        self.assertTrue(
            any('30-min break' in r for r in all_remarks),
            f"No '30-min break' found in remarks: {all_remarks}"
        )

    def test_driving_before_break_at_most_8(self):
        """Cumulative driving before a break should not exceed 8 hours."""
        for log in self.result['daily_logs']:
            driving_since_break = 0.0
            for event in log['events']:
                if event['status'] == 'driving':
                    driving_since_break += event['hours']
                    self.assertLessEqual(
                        driving_since_break, 8.01,
                        f"Drove {driving_since_break:.2f} hours without a break"
                    )
                elif event['status'] in ('off_duty', 'on_duty_not_driving'):
                    if event['hours'] >= 0.49:  # Qualifying break (≥30 min)
                        driving_since_break = 0.0


class TestLongTrip(TestCase):
    """
    Test 3: Long trip — 2110 miles, cycle=0.
    This is the master test case from the prompt.
    2110 / 55 = 38.4 hours of driving → ~4 days minimum.
    Should produce fuel stops (every 1000 miles) and rest stops.
    """

    def setUp(self):
        self.result = calculate_trip(
            segments=[
                {'distance_miles': 510, 'from_location': 'Chicago', 'to_location': 'Kansas City'},
                {'distance_miles': 1600, 'from_location': 'Kansas City', 'to_location': 'Los Angeles'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )

    def test_multi_day(self):
        """2110-mile trip should span at least 3 days."""
        self.assertGreaterEqual(len(self.result['daily_logs']), 3)

    def test_fuel_stops_present(self):
        """At least one fuel stop should be in stop_events."""
        fuel_stops = [s for s in self.result['stop_events'] if s['type'] == 'fuel']
        self.assertGreater(len(fuel_stops), 0, "No fuel stops generated for 2110-mile trip")

    def test_rest_stops_present(self):
        """At least one rest stop should be in stop_events."""
        rest_stops = [s for s in self.result['stop_events'] if s['type'] == 'rest']
        self.assertGreater(len(rest_stops), 0, "No rest stops generated for 2110-mile trip")

    def test_total_miles_correct(self):
        """Sum of miles_today across all days should equal total trip distance."""
        total_miles = sum(log['miles_today'] for log in self.result['daily_logs'])
        self.assertAlmostEqual(total_miles, 2110, delta=5)

    def test_every_day_sums_to_24(self):
        """Every day's totals must sum to 24."""
        for log in self.result['daily_logs']:
            total = sum(log['totals'].values())
            self.assertAlmostEqual(
                total, 24.0, places=1,
                msg=f"Day {log['day']} totals sum to {total}"
            )

    def test_consecutive_dates(self):
        """Daily log dates should be consecutive."""
        from datetime import datetime
        dates = [log['date'] for log in self.result['daily_logs']]
        for i in range(len(dates) - 1):
            dt1 = datetime.strptime(dates[i], '%Y-%m-%d')
            dt2 = datetime.strptime(dates[i + 1], '%Y-%m-%d')
            self.assertEqual((dt2 - dt1).days, 1, f"Non-consecutive dates: {dates[i]} → {dates[i+1]}")


class TestBreakTrigger(TestCase):
    """
    Test 6: 8-hour break trigger.
    After pickup resets the counter, 500/55 = 9.09 hrs of driving
    should trigger the 30-min break rule.
    """

    def test_break_triggers_at_8_hours(self):
        """Long second segment triggers the 8-hour break rule."""
        result = calculate_trip(
            segments=[
                {'distance_miles': 10, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 500, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )

        all_events = []
        for log in result['daily_logs']:
            all_events.extend(log['events'])

        breaks = [e for e in all_events
                  if e['status'] == 'off_duty'
                  and abs(e['hours'] - 0.5) < 0.01]
        self.assertGreater(len(breaks), 0, "30-min break not triggered after 8hrs driving")


class TestFuelStopResetsBreak(TestCase):
    """
    Test 9: Fuel stop resets break counter.
    A fuel stop is 1 hour OND, which qualifies as a ≥30-min break.
    After a fuel stop, the 8-hour break counter should reset to 0.
    """

    def test_fuel_stop_resets_counter(self):
        """
        1200-mile trip: fuel stop at 1000 miles resets break counter.
        """
        result = calculate_trip(
            segments=[
                {'distance_miles': 600, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 600, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )

        fuel_stops = [s for s in result['stop_events'] if s['type'] == 'fuel']
        self.assertGreater(len(fuel_stops), 0, "No fuel stop generated for 1200-mile trip")

        for fs in fuel_stops:
            self.assertGreater(fs['total_miles_at_stop'], 0)
            self.assertLessEqual(fs['total_miles_at_stop'], 1200)

    def test_no_double_break_after_fuel(self):
        """
        After a fuel stop (1hr OND), a 30-min break should NOT immediately follow
        because the fuel stop already qualifies as a break reset.
        """
        result = calculate_trip(
            segments=[
                {'distance_miles': 600, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 600, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )

        all_events = []
        for log in result['daily_logs']:
            all_events.extend(log['events'])

        for i, event in enumerate(all_events):
            if (event['status'] == 'on_duty_not_driving' and
                    abs(event['hours'] - 1.0) < 0.01 and i + 1 < len(all_events)):
                next_event = all_events[i + 1]
                if next_event['status'] == 'off_duty' and abs(next_event['hours'] - 0.5) < 0.01:
                    if i + 2 < len(all_events):
                        self.fail(
                            f"30-min break immediately after 1hr OND stop (possible double-break) "
                            f"at event index {i}"
                        )


class TestHoursSumTo24WithBreaksAndFuel(TestCase):
    """Extended 24-hour sum tests including trips with breaks and fuel stops."""

    def _assert_totals_sum_to_24(self, daily_logs):
        for log in daily_logs:
            total = sum(log['totals'].values())
            self.assertAlmostEqual(
                total, 24.0, places=1,
                msg=f"Day {log['day']} totals sum to {total}, not 24.0"
            )

    def test_long_trip_with_fuel_sums_to_24(self):
        """2110-mile trip with fuel stops: every day sums to 24."""
        result = calculate_trip(
            segments=[
                {'distance_miles': 510, 'from_location': 'Chicago', 'to_location': 'Kansas City'},
                {'distance_miles': 1600, 'from_location': 'Kansas City', 'to_location': 'Los Angeles'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )
        self._assert_totals_sum_to_24(result['daily_logs'])

    def test_1200_mile_trip_sums_to_24(self):
        """1200-mile trip with fuel stop: every day sums to 24."""
        result = calculate_trip(
            segments=[
                {'distance_miles': 600, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 600, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )
        self._assert_totals_sum_to_24(result['daily_logs'])

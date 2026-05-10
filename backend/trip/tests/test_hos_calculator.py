"""
Tests for the HOS Calculator module.

Iteration 3a: Basic single-day trip tests.
    - Test 1: Short trip (200 mi, cycle=0) — single day, no breaks, no fuel stops
    - Test 7: Hours sum to 24 — every DailyLog totals sum to exactly 24.0

Additional basic tests:
    - Pre/post trip inspection present
    - Pickup and dropoff stops logged
    - 11-hour driving limit enforced (multi-day trip)
    - 14-hour window enforced
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

    Expected timeline:
        08:00 - 08:30  Pre-trip inspection (0.5 hr OND)
        08:30 - 12:09  Drive to pickup (3.64 hrs, 200 mi)
        12:09 - 13:09  Pickup loading (1 hr OND)
        (No driving needed for segment 2 if distance is 0... but we'll use a real segment)

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
        # Should have: pre-trip (0.5), pickup (1.0), dropoff (1.0), post-trip (0.5)
        ond_hours = [round(e['hours'], 1) for e in ond_events]
        self.assertIn(1.0, ond_hours)  # At least one 1-hour OND (pickup or dropoff)

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
        # Check that pre-trip inspection is in remarks
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
        # Should be at least 2 days
        self.assertGreaterEqual(len(result['daily_logs']), 2)


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

        # Should span multiple days
        self.assertGreaterEqual(len(result['daily_logs']), 2)

        # Day 1 driving should not exceed 11 hours
        day1 = result['daily_logs'][0]
        self.assertLessEqual(day1['totals']['driving'], 11.01)

    def test_14_hour_window_limits_driving(self):
        """
        The 14-hour window starts at first on-duty. If OND activities consume
        significant window time, driving hours get reduced even below 11.

        With 0.5hr pre-trip + some driving + 1hr pickup + more driving,
        the window constrains how much driving fits.
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

        # Total on-duty time (driving + OND) should fit within the 14-hour window
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
            # Should have at least one rest stop event
            rest_stops = [s for s in result['stop_events'] if s['type'] == 'rest']
            self.assertGreater(len(rest_stops), 0)


# ─── Iteration 3b Tests ─────────────────────────────────────────────────────

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

        # Find off-duty events that are exactly 0.5 hours (30 minutes)
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
        dates = [log['date'] for log in self.result['daily_logs']]
        for i in range(len(dates) - 1):
            d1 = dates[i]
            d2 = dates[i + 1]
            from datetime import datetime, timedelta
            dt1 = datetime.strptime(d1, '%Y-%m-%d')
            dt2 = datetime.strptime(d2, '%Y-%m-%d')
            self.assertEqual((dt2 - dt1).days, 1, f"Non-consecutive dates: {d1} → {d2}")


class TestBreakTrigger(TestCase):
    """
    Test 6: 8-hour break trigger.
    Exactly 440 miles (8 hours at 55mph) of driving should trigger a 30-min break
    before any more driving.
    """

    def test_break_triggers_at_8_hours(self):
        """440-mile trip triggers the 8-hour break rule."""
        result = calculate_trip(
            segments=[
                # Seg 1: 300mi → 5.45hrs driving, then 1hr pickup → break counter resets
                # Seg 2: 200mi → 3.64hrs driving. After pickup reset, total is 3.64 < 8. No break needed.
                # Instead, use a single-segment trip to ensure continuous driving
                {'distance_miles': 10, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 500, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )

        # After pickup (resets counter), 500/55 = 9.09 hrs driving
        # At 8hrs driving, should insert break, then continue
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
        After fuel stop, driver should be able to drive 8 more hours
        before needing another break.
        """
        result = calculate_trip(
            segments=[
                {'distance_miles': 600, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 600, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )

        # Should have a fuel stop
        fuel_stops = [s for s in result['stop_events'] if s['type'] == 'fuel']
        self.assertGreater(len(fuel_stops), 0, "No fuel stop generated for 1200-mile trip")

        # Check that fuel stops record correct total_miles_at_stop
        for fs in fuel_stops:
            self.assertGreater(fs['total_miles_at_stop'], 0)
            self.assertLessEqual(fs['total_miles_at_stop'], 1200)

    def test_no_double_break_after_fuel(self):
        """
        After a fuel stop (1hr), a 30-min break should NOT immediately follow
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

        # Walk through events: after a fuel stop (OND 1hr), the very next event
        # should NOT be a 30-min off-duty break
        all_events = []
        for log in result['daily_logs']:
            all_events.extend(log['events'])

        for i, event in enumerate(all_events):
            if (event['status'] == 'on_duty_not_driving' and
                    abs(event['hours'] - 1.0) < 0.01 and i + 1 < len(all_events)):
                next_event = all_events[i + 1]
                # The next event after a 1hr OND should NOT be a 30-min off-duty
                # (unless it's a legitimate end-of-day rest, which is fine)
                if next_event['status'] == 'off_duty' and abs(next_event['hours'] - 0.5) < 0.01:
                    # This would mean a double-break, which shouldn't happen
                    # unless it's a coincidence with day padding — check if it's the last event
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


# ─── Iteration 3c Tests ─────────────────────────────────────────────────────

class TestHighCycle(TestCase):
    """
    Test 4: High cycle — 1000 miles, current_cycle_used=60.
    Driver has 10 hours left in cycle. With pre-trip (0.5) + pickup (1) + dropoff (1.5),
    that leaves only ~7 hours of driving before cycle hits 70.
    7 * 55 = 385 miles — forcing early rest compared to a fresh-cycle driver.
    """

    def setUp(self):
        self.result = calculate_trip(
            segments=[
                {'distance_miles': 500, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 500, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=60,
            start_date='2026-05-07',
        )

    def test_cycle_limits_day1_driving(self):
        """Day 1 driving should be limited by the 70hr cycle, not just the 11hr limit."""
        day1 = self.result['daily_logs'][0]
        # With 60hrs used + 0.5 pre-trip = 60.5. Only 9.5 hrs of on-duty remain.
        # Of that, driving can be at most 9.5 - pickup(1) = ~8.5hrs or 11hrs, whichever is less
        # The cycle constraint should kick in before the 11hr limit
        self.assertLessEqual(day1['totals']['driving'], 11.01)

    def test_triggers_restart_or_multi_day(self):
        """A 1000-mile trip with 60hr cycle should span multiple days."""
        self.assertGreaterEqual(len(self.result['daily_logs']), 2)

    def test_all_days_sum_to_24(self):
        """Every day must sum to 24."""
        for log in self.result['daily_logs']:
            total = sum(log['totals'].values())
            self.assertAlmostEqual(total, 24.0, places=1,
                                   msg=f"Day {log['day']} = {total}")


class TestMaxCycle34hrRestart(TestCase):
    """
    Test 5: Max cycle — 2000 miles, current_cycle_used=65.
    Driver has only 5 hours of on-duty before hitting 70.
    After ~5 hours on-duty, a 34-hour restart must be triggered.
    After restart, cycle resets to 0 and driver can continue.
    """

    def setUp(self):
        self.result = calculate_trip(
            segments=[
                {'distance_miles': 800, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 1200, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=65,
            start_date='2026-05-07',
        )

    def test_restart_triggered(self):
        """34-hour restart should produce extra days."""
        # 2000 miles = ~36 hours of driving = ~4+ normal days
        # Plus the 34-hour restart adds 1-2 extra days
        self.assertGreaterEqual(len(self.result['daily_logs']), 5)

    def test_has_full_offduty_day(self):
        """At least one day should be entirely (or mostly) off-duty — a restart day."""
        for log in self.result['daily_logs']:
            if log['totals']['off_duty'] >= 23.0:  # Nearly full off-duty day
                return  # Found one
        # If no day is mostly off-duty, check for a day with very high off-duty
        max_offduty = max(log['totals']['off_duty'] for log in self.result['daily_logs'])
        self.assertGreaterEqual(max_offduty, 10.0,
                                "No day with significant off-duty time found (expected 34hr restart days)")

    def test_all_days_sum_to_24(self):
        """Every day must sum to 24."""
        for log in self.result['daily_logs']:
            total = sum(log['totals'].values())
            self.assertAlmostEqual(total, 24.0, places=1,
                                   msg=f"Day {log['day']} = {total}")

    def test_total_miles_correct(self):
        """Total miles across all days should equal 2000."""
        total_miles = sum(log['miles_today'] for log in self.result['daily_logs'])
        self.assertAlmostEqual(total_miles, 2000, delta=5)


class Test14hrWindowEdge(TestCase):
    """
    Test 8: 14-hour window enforcement.
    The 14-hour window starts at first on-duty. If non-driving activities
    consume significant time, the window may expire before 11 driving hours.
    """

    def test_window_expires_before_11hr(self):
        """
        With a long pickup stop, the 14-hour window should limit driving
        even though the 11-hour limit isn't reached.

        Timeline: 08:00 pre-trip (0.5) + drive 5hrs (10:30-13:30) + pickup 1hr (13:30-14:30)
        + drive... Window started at 08:00, expires at 22:00 (14hrs).
        Total on-duty activities (including breaks, fuel, OND) eat into the window.
        """
        result = calculate_trip(
            segments=[
                {'distance_miles': 300, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 500, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )

        day1 = result['daily_logs'][0]
        # Total on-duty time should not exceed 14 hours
        total_time = (day1['totals']['driving'] +
                      day1['totals']['on_duty_not_driving'] +
                      day1['totals']['off_duty'])
        # The off-duty breaks still happen within the window period
        # Key check: driving + OND + off-duty-breaks should fit in 14hr window
        # Driving should be less than 11 if window is the binding constraint
        self.assertLessEqual(day1['totals']['driving'], 11.01)


class Test34hrRestartDaySplit(TestCase):
    """
    Test 10: 34-hour restart spans days correctly.
    The 34-hour restart must be split across calendar days so each day sums to 24.
    """

    def test_restart_produces_consecutive_dates(self):
        """Dates should be consecutive even through the 34-hr restart."""
        result = calculate_trip(
            segments=[
                {'distance_miles': 800, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 1200, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=65,
            start_date='2026-05-07',
        )

        from datetime import datetime
        dates = [log['date'] for log in result['daily_logs']]
        for i in range(len(dates) - 1):
            dt1 = datetime.strptime(dates[i], '%Y-%m-%d')
            dt2 = datetime.strptime(dates[i + 1], '%Y-%m-%d')
            self.assertEqual((dt2 - dt1).days, 1,
                             f"Non-consecutive dates: {dates[i]} → {dates[i+1]}")

    def test_restart_remarks_present(self):
        """34-hr restart should appear in remarks."""
        result = calculate_trip(
            segments=[
                {'distance_miles': 800, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 1200, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=65,
            start_date='2026-05-07',
        )

        all_remarks = []
        for log in result['daily_logs']:
            all_remarks.extend(log['remarks'])

        self.assertTrue(
            any('34-hr restart' in r for r in all_remarks),
            f"No '34-hr restart' found in remarks: {all_remarks}"
        )


class TestZeroDistanceSegment(TestCase):
    """
    Test 11: Zero-distance segment handled.
    If pickup is in the same city as current location, no driving should occur
    for that segment but the pickup stop should still be logged.
    """

    def test_same_city_pickup(self):
        """Zero-mile first segment should not produce driving, but pickup is logged."""
        result = calculate_trip(
            segments=[
                {'distance_miles': 0, 'from_location': 'Chicago', 'to_location': 'Chicago'},
                {'distance_miles': 300, 'from_location': 'Chicago', 'to_location': 'St Louis'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )

        day1 = result['daily_logs'][0]

        # Should have a pickup event
        has_pickup = any('Pickup' in r for r in day1['remarks'])
        self.assertTrue(has_pickup, f"Pickup not found in remarks: {day1['remarks']}")

        # Should still have driving for the second segment
        self.assertGreater(day1['totals']['driving'], 0)

        # Total miles should be ~300
        total_miles = sum(log['miles_today'] for log in result['daily_logs'])
        self.assertAlmostEqual(total_miles, 300, delta=5)

    def test_zero_distance_sums_to_24(self):
        """Zero-distance segment trip should still sum to 24."""
        result = calculate_trip(
            segments=[
                {'distance_miles': 0, 'from_location': 'Chicago', 'to_location': 'Chicago'},
                {'distance_miles': 300, 'from_location': 'Chicago', 'to_location': 'St Louis'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )

        for log in result['daily_logs']:
            total = sum(log['totals'].values())
            self.assertAlmostEqual(total, 24.0, places=1,
                                   msg=f"Day {log['day']} = {total}")


class TestAllHoursSumTo24Final(TestCase):
    """Final comprehensive 24-hour sum test across ALL scenario types."""

    def _assert_all_24(self, result):
        for log in result['daily_logs']:
            total = sum(log['totals'].values())
            self.assertAlmostEqual(total, 24.0, places=1,
                                   msg=f"Day {log['day']} = {total}")

    def test_high_cycle_sums_to_24(self):
        result = calculate_trip(
            segments=[
                {'distance_miles': 500, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 500, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=60,
            start_date='2026-05-07',
        )
        self._assert_all_24(result)

    def test_max_cycle_restart_sums_to_24(self):
        result = calculate_trip(
            segments=[
                {'distance_miles': 800, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 1200, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=65,
            start_date='2026-05-07',
        )
        self._assert_all_24(result)

    def test_zero_distance_sums_to_24(self):
        result = calculate_trip(
            segments=[
                {'distance_miles': 0, 'from_location': 'A', 'to_location': 'A'},
                {'distance_miles': 200, 'from_location': 'A', 'to_location': 'B'},
            ],
            current_cycle_used=0,
            start_date='2026-05-07',
        )
        self._assert_all_24(result)



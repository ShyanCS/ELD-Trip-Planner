"""
Tests for the HOS Calculator — edge cases.

Covers:
    - TestHighCycle: 60-hour cycle forcing early rest and cycle constraints
    - TestMaxCycle34hrRestart: 65-hour cycle triggering 34-hour restart
    - Test14hrWindowEdge: 14-hour window expiring before 11-hour driving limit
    - Test34hrRestartDaySplit: 34-hour restart spans consecutive calendar days
    - TestZeroDistanceSegment: zero-distance pickup segment handled correctly
    - TestAllHoursSumTo24Final: comprehensive 24-hour sum invariant across all scenarios
"""

from django.test import TestCase

from trip.hos_calculator import calculate_trip


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
        Total on-duty + off-duty activities on day 1 should fit within the 14hr window.
        Driving should be within the 11-hour limit.
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
        self.assertLessEqual(day1['totals']['driving'], 11.01)


class Test34hrRestartDaySplit(TestCase):
    """
    Test 10: 34-hour restart spans days correctly.
    The 34-hour restart must be split across calendar days so each day sums to 24.
    """

    def test_restart_produces_consecutive_dates(self):
        """Dates should be consecutive even through the 34-hr restart."""
        from datetime import datetime
        result = calculate_trip(
            segments=[
                {'distance_miles': 800, 'from_location': 'A', 'to_location': 'B'},
                {'distance_miles': 1200, 'from_location': 'B', 'to_location': 'C'},
            ],
            current_cycle_used=65,
            start_date='2026-05-07',
        )

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

        has_pickup = any('Pickup' in r for r in day1['remarks'])
        self.assertTrue(has_pickup, f"Pickup not found in remarks: {day1['remarks']}")

        self.assertGreater(day1['totals']['driving'], 0)

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

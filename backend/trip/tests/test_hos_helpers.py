"""
Unit tests for the pure HOS helper primitives (trip.hos_helpers).
"""

from django.test import TestCase

from trip.hos_helpers import (
    add_remark,
    assert_24h_invariant,
    compute_day_totals,
    hours_to_time_str,
    make_event,
)


class HoursToTimeStrTests(TestCase):
    def test_known_conversions(self):
        self.assertEqual(hours_to_time_str(0.0), '00:00')
        self.assertEqual(hours_to_time_str(8.0), '08:00')
        self.assertEqual(hours_to_time_str(8.5), '08:30')
        self.assertEqual(hours_to_time_str(13.25), '13:15')
        self.assertEqual(hours_to_time_str(23.75), '23:45')
        self.assertEqual(hours_to_time_str(12.0), '12:00')

    def test_rounding_carry_minutes(self):
        # 60 rounded minutes must carry into the next hour
        self.assertEqual(hours_to_time_str(7.999), '08:00')

    def test_wraps_past_midnight(self):
        self.assertEqual(hours_to_time_str(24.5), '00:30')


class MakeEventTests(TestCase):
    def test_event_fields_are_serializable_and_rounded(self):
        event = make_event(8.5, 'driving', 'Chicago', 3.14159265, 172.949)
        self.assertEqual(event, {
            'time': '08:30',
            'status': 'driving',
            'location': 'Chicago',
            'hours': 3.1416,
            'miles': 172.9,
        })


class AddRemarkTests(TestCase):
    def test_remark_format(self):
        remarks = []
        add_remark(remarks, 9.25, 'Springfield', 'Fuel stop')
        self.assertEqual(remarks, ['09:15 Springfield - Fuel stop'])


class ComputeDayTotalsTests(TestCase):
    def test_all_statuses_present_with_zero_defaults(self):
        totals = compute_day_totals([])
        self.assertEqual(totals, {
            'off_duty': 0.0,
            'sleeper_berth': 0.0,
            'driving': 0.0,
            'on_duty_not_driving': 0.0,
        })

    def test_sums_per_status_and_rounds(self):
        events = [
            make_event(0.0, 'off_duty', 'A', 10.0),
            make_event(10.0, 'on_duty_not_driving', 'A', 1.0),
            make_event(11.0, 'driving', 'A', 11.0),
            make_event(22.0, 'off_duty', 'A', 2.0),
        ]
        totals = compute_day_totals(events)
        self.assertEqual(totals['off_duty'], 12.0)
        self.assertEqual(totals['driving'], 11.0)
        self.assertEqual(totals['on_duty_not_driving'], 1.0)
        self.assertEqual(totals['sleeper_berth'], 0.0)


class Assert24hInvariantTests(TestCase):
    def test_passes_on_exact_24(self):
        totals = {'off_duty': 13.0, 'sleeper_berth': 0.0, 'driving': 11.0, 'on_duty_not_driving': 0.0}
        assert_24h_invariant(totals, day_number=1)  # should not raise

    def test_raises_on_broken_total(self):
        totals = {'off_duty': 20.0, 'sleeper_berth': 0.0, 'driving': 11.0, 'on_duty_not_driving': 0.0}
        with self.assertRaises(AssertionError) as ctx:
            assert_24h_invariant(totals, day_number=3)
        self.assertIn('Day 3', str(ctx.exception))

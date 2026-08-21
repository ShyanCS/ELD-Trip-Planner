"""
Tests for TripPlanSerializer — field-level and cross-field validation.

Covers:
    - TestLocationRegexValidator: valid and invalid location strings
    - TestCycleHoursValidator: boundary values for current_cycle_used
    - TestCrossFieldValidation: pickup != dropoff requirement
    - TestStartDateField: optional date field parsing
"""

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from trip.serializers import TripPlanSerializer


VALID_BASE = {
    'current_location': 'Chicago, IL',
    'pickup_location': 'Kansas City, MO',
    'dropoff_location': 'Los Angeles, CA',
    'current_cycle_used': 20,
}


class TestLocationRegexValidator(TestCase):
    """Tests for _location_validator RegexValidator on location fields."""

    def _assert_valid(self, location):
        """Assert that the given location passes validation."""
        data = {**VALID_BASE, 'current_location': location}
        s = TripPlanSerializer(data=data)
        self.assertTrue(s.is_valid(), f"Expected valid for: {location!r}  Errors: {s.errors}")

    def _assert_invalid(self, location):
        """Assert that the given location fails validation."""
        data = {**VALID_BASE, 'current_location': location}
        s = TripPlanSerializer(data=data)
        self.assertFalse(s.is_valid(), f"Expected invalid for: {location!r}")

    def test_plain_city_state_is_valid(self):
        self._assert_valid('Chicago, IL')

    def test_city_with_hyphen_is_valid(self):
        self._assert_valid('Winston-Salem, NC')

    def test_street_address_is_valid(self):
        self._assert_valid('123 Main St, Springfield, IL')

    def test_script_tag_is_invalid(self):
        self._assert_invalid('<script>alert(1)</script>')

    def test_sql_injection_is_invalid(self):
        self._assert_invalid("'; DROP TABLE users; --")

    def test_empty_string_is_invalid(self):
        data = {**VALID_BASE, 'current_location': '   '}
        s = TripPlanSerializer(data=data)
        self.assertFalse(s.is_valid())


class TestCycleHoursValidator(TestCase):
    """Tests for min_value/max_value on current_cycle_used."""

    def test_zero_is_valid(self):
        s = TripPlanSerializer(data={**VALID_BASE, 'current_cycle_used': 0})
        self.assertTrue(s.is_valid(), s.errors)

    def test_seventy_is_valid(self):
        s = TripPlanSerializer(data={**VALID_BASE, 'current_cycle_used': 70})
        self.assertTrue(s.is_valid(), s.errors)

    def test_negative_is_invalid(self):
        s = TripPlanSerializer(data={**VALID_BASE, 'current_cycle_used': -0.1})
        self.assertFalse(s.is_valid())

    def test_over_seventy_is_invalid(self):
        s = TripPlanSerializer(data={**VALID_BASE, 'current_cycle_used': 70.1})
        self.assertFalse(s.is_valid())


class TestCrossFieldValidation(TestCase):
    """Tests for the cross-field pickup != dropoff rule."""

    def test_same_pickup_dropoff_is_invalid(self):
        data = {
            **VALID_BASE,
            'pickup_location': 'Kansas City, MO',
            'dropoff_location': 'Kansas City, MO',
        }
        s = TripPlanSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn('dropoff_location', s.errors)

    def test_case_insensitive_same_is_invalid(self):
        data = {
            **VALID_BASE,
            'pickup_location': 'kansas city, mo',
            'dropoff_location': 'Kansas City, MO',
        }
        s = TripPlanSerializer(data=data)
        self.assertFalse(s.is_valid())

    def test_different_cities_is_valid(self):
        s = TripPlanSerializer(data=VALID_BASE)
        self.assertTrue(s.is_valid(), s.errors)


class TestStartDateField(TestCase):
    """Tests for optional start_date field."""

    def test_omitted_start_date_is_valid(self):
        s = TripPlanSerializer(data=VALID_BASE)
        self.assertTrue(s.is_valid(), s.errors)
        self.assertNotIn('start_date', s.errors)

    def test_valid_iso_date_accepted(self):
        s = TripPlanSerializer(data={**VALID_BASE, 'start_date': '2026-05-07'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_invalid_date_format_rejected(self):
        s = TripPlanSerializer(data={**VALID_BASE, 'start_date': 'not-a-date'})
        self.assertFalse(s.is_valid())

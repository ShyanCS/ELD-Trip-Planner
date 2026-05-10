"""
Trip serializers — input validation for trip planning requests.
"""

from rest_framework import serializers


class TripPlanSerializer(serializers.Serializer):
    """
    Validates the trip planning input from the frontend.

    Fields:
        current_location:  City/address where the driver currently is
        pickup_location:   City/address where the load is picked up
        dropoff_location:  City/address where the load is delivered
        current_cycle_used: Hours already used in the 70-hour/8-day rolling window (0-70)
        start_date:        Optional trip start date (YYYY-MM-DD, defaults to today)
    """
    current_location = serializers.CharField(
        max_length=200,
        help_text="Driver's current city/address, e.g. 'Chicago, IL'"
    )
    pickup_location = serializers.CharField(
        max_length=200,
        help_text="Load pickup city/address, e.g. 'Kansas City, MO'"
    )
    dropoff_location = serializers.CharField(
        max_length=200,
        help_text="Load dropoff city/address, e.g. 'Los Angeles, CA'"
    )
    current_cycle_used = serializers.FloatField(
        min_value=0,
        max_value=70,
        help_text="Hours used in the 70-hour/8-day rolling window (0-70)"
    )
    start_date = serializers.DateField(
        required=False,
        help_text="Trip start date (YYYY-MM-DD). Defaults to today."
    )

    def validate_current_location(self, value):
        """Strip whitespace and ensure non-empty."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Current location cannot be empty.")
        return value

    def validate_pickup_location(self, value):
        """Strip whitespace and ensure non-empty."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Pickup location cannot be empty.")
        return value

    def validate_dropoff_location(self, value):
        """Strip whitespace and ensure non-empty."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Dropoff location cannot be empty.")
        return value

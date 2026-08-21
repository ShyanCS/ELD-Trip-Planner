"""
HOS Data Classes — shared data structures for the HOS calculator.

Extracted from hos_calculator.py to keep the core calculation logic focused
and to make the data structures importable elsewhere (e.g. type hints in views).
"""

from dataclasses import dataclass, field


@dataclass
class DutyEvent:
    """A single duty status change event in a driver's day."""
    time: str               # "HH:MM" format
    status: str             # "off_duty" | "sleeper_berth" | "driving" | "on_duty_not_driving"
    location: str           # City, State
    hours: float            # Duration of this event in hours
    miles: float = 0.0      # Miles driven during this event (0 for non-driving)


@dataclass
class DailyLog:
    """A complete daily log for one day."""
    day: int                                # Day number (1-indexed)
    date: str                               # "YYYY-MM-DD" format
    events: list = field(default_factory=list)   # List of DutyEvent dicts
    totals: dict = field(default_factory=dict)   # {off_duty, sleeper_berth, driving, on_duty_not_driving}
    miles_today: float = 0.0                # Miles driven THIS day only
    remarks: list = field(default_factory=list)   # ["HH:MM Location - Activity"]


@dataclass
class StopEvent:
    """A stop that needs a map waypoint (fuel stop or rest stop)."""
    type: str               # "fuel" | "rest"
    location_name: str      # Best-effort name
    total_miles_at_stop: float  # Miles from trip start — used by views.py for geo-placement

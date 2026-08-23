"""
HOS helper functions — pure event-construction and day-totalization primitives.

Extracted from hos_calculator.py so the engine can focus on orchestration.
Everything here is side-effect-free except for mutation of the remarks list
explicitly passed in by the caller.
"""

HOURS_IN_DAY = 24.0

STATUS_KEYS = ('off_duty', 'sleeper_berth', 'driving', 'on_duty_not_driving')


def hours_to_time_str(hours_since_midnight):
    """Convert decimal hours to HH:MM string. E.g. 13.5 -> '13:30'."""
    h = int(hours_since_midnight) % 24
    m = int(round((hours_since_midnight % 1) * 60))
    if m == 60:
        h += 1
        m = 0
    return f"{h:02d}:{m:02d}"


def make_event(time_hours, status, location, duration, miles=0.0):
    """Create a DutyEvent dict (serializable)."""
    return {
        'time': hours_to_time_str(time_hours),
        'status': status,
        'location': location,
        'hours': round(duration, 4),
        'miles': round(miles, 1),
    }


def add_remark(remarks, time_hours, location, activity):
    """Add an entry to the remarks list."""
    time_str = hours_to_time_str(time_hours)
    remarks.append(f"{time_str} {location} - {activity}")


def compute_day_totals(events):
    """
    Sum per-status hour totals for one day's events.

    Returns a dict keyed by every HOS status (missing statuses are 0.0),
    rounded for clean output.
    """
    totals = {status: 0.0 for status in STATUS_KEYS}
    for e in events:
        totals[e['status']] = round(totals[e['status']] + e['hours'], 4)

    # Round totals for clean output
    for k in totals:
        totals[k] = round(totals[k], 2)
    return totals


def assert_24h_invariant(totals, day_number):
    """
    Assert that a day's totals sum to exactly 24 hours.

    This is the core FMCSA invariant of every daily log; violations indicate
    an engine bug and must fail loudly rather than render an invalid log.
    """
    total_sum = sum(totals.values())
    assert abs(total_sum - HOURS_IN_DAY) < 0.02, (
        f"Day {day_number} totals sum to {total_sum}, expected {HOURS_IN_DAY}."
    )

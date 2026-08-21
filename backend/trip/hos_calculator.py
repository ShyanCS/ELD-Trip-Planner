"""
HOS Calculator — Hours of Service compliance engine for FMCSA regulations.

This is the core of the ELD Trip Planner. It takes route segments and produces
day-by-day event timelines that comply with all FMCSA HOS rules.

FMCSA Rules Implemented:
    - Max 11 hours driving per day (within 14-hour window)
    - 14-hour driving window starts when first on-duty
    - 10 consecutive hours off-duty required before next window
    - 30-minute break after 8 cumulative driving hours
    - Fuel stop every 1,000 miles (1 hour OND)
    - Fuel/pickup stops >= 30 min reset the break counter
    - 70-hour / 8-day rolling limit
    - 34-hour restart when cycle exhausted (split across calendar days)

Assumptions (fixed):
    - Property-carrying CMV driver
    - 70-hour / 8-day rule
    - Driver speed: 55 mph average
    - Fueling every 1,000 miles (1 hour OND stop) (Iteration 3b)
    - 1 hour for pickup (OND)
    - 1 hour for dropoff (OND)
    - Pre/post trip inspection: 30 minutes OND
"""

from dataclasses import field  # noqa: F401 — re-exported for backward compat
from datetime import datetime, timedelta

from .models_dataclasses import DailyLog, DutyEvent, StopEvent  # noqa: F401

# ─── Constants ───────────────────────────────────────────────────────────────

DRIVER_SPEED_MPH = 55
MAX_DRIVING_HOURS = 11.0
MAX_WINDOW_HOURS = 14.0
MANDATORY_REST_HOURS = 10.0
HOURS_IN_DAY = 24.0
PRE_POST_TRIP_HOURS = 0.5       # 30 minutes
PICKUP_DROPOFF_HOURS = 1.0      # 1 hour
BREAK_THRESHOLD_HOURS = 8.0     # 30-min break after 8 hrs driving
BREAK_DURATION_HOURS = 0.5      # 30 minutes
FUEL_INTERVAL_MILES = 1000
FUEL_STOP_HOURS = 1.0           # 1 hour
MAX_CYCLE_HOURS = 70.0
RESTART_HOURS = 34.0
DEFAULT_START_HOUR = 8.0        # 08:00



# ─── Helper Functions ────────────────────────────────────────────────────────

def _hours_to_time_str(hours_since_midnight):
    """Convert decimal hours to HH:MM string. E.g. 13.5 -> '13:30'."""
    h = int(hours_since_midnight) % 24
    m = int(round((hours_since_midnight % 1) * 60))
    if m == 60:
        h += 1
        m = 0
    return f"{h:02d}:{m:02d}"


def _make_event(time_hours, status, location, duration, miles=0.0):
    """Create a DutyEvent dict (serializable)."""
    return {
        'time': _hours_to_time_str(time_hours),
        'status': status,
        'location': location,
        'hours': round(duration, 4),
        'miles': round(miles, 1),
    }


def _add_remark(remarks, time_hours, location, activity):
    """Add an entry to the remarks list."""
    time_str = _hours_to_time_str(time_hours)
    remarks.append(f"{time_str} {location} - {activity}")


# ─── Main Calculator ────────────────────────────────────────────────────────

def calculate_trip(segments, current_cycle_used=0.0, start_date=None):
    """
    Calculate HOS-compliant trip plan with daily logs.

    Args:
        segments: List of dicts, each with:
            - distance_miles: float
            - from_location: str (city name)
            - to_location: str (city name)
        current_cycle_used: Hours already used in 8-day rolling window (0-70)
        start_date: Optional start date string "YYYY-MM-DD", defaults to today

    Returns:
        dict: {
            daily_logs: list of DailyLog-like dicts,
            stop_events: list of StopEvent-like dicts (for map waypoints)
        }
    """
    if start_date is None:
        start_date = datetime.now().strftime('%Y-%m-%d')

    # ─── State Variables ─────────────────────────────────────────────
    current_time = DEFAULT_START_HOUR       # Hours since midnight
    driving_hours_today = 0.0               # Cumulative driving in current duty period (max 11)
    window_start = DEFAULT_START_HOUR       # When the 14-hour window began
    hours_since_last_break = 0.0            # Cumulative driving since last qualifying break (max 8)
    cycle_hours_used = current_cycle_used   # Total on-duty in 8-day rolling window (max 70)
    day_number = 1
    miles_since_last_fuel = 0.0             # Miles driven since last fuel stop (max 1000)
    miles_today = 0.0                       # Miles driven in current day
    total_miles_driven = 0.0                # Running total from trip start

    # Current day accumulators
    day_events = []
    day_remarks = []

    # Output collectors
    daily_logs = []
    stop_events = []

    # Calculate the date for a given day number
    base_date = datetime.strptime(start_date, '%Y-%m-%d')

    def _current_date():
        return (base_date + timedelta(days=day_number - 1)).strftime('%Y-%m-%d')

    def _window_remaining():
        """Hours remaining in the 14-hour window."""
        elapsed = current_time - window_start
        return max(0.0, MAX_WINDOW_HOURS - elapsed)

    def _hours_remaining_in_day():
        """Hours remaining until midnight (24:00). Prevents day overflow."""
        return max(0.0, HOURS_IN_DAY - current_time)

    def _finalize_day():
        """Pad the current day to 24 hours and finalize it."""
        nonlocal current_time, day_events, day_remarks, miles_today

        time_used = sum(e['hours'] for e in day_events)
        remaining = HOURS_IN_DAY - time_used

        if remaining > 0.001:  # Small epsilon to avoid floating point noise
            # Determine location from last event
            last_location = day_events[-1]['location'] if day_events else 'Unknown'
            day_events.append(_make_event(current_time, 'off_duty', last_location, remaining))

        # Calculate totals
        totals = {
            'off_duty': 0.0,
            'sleeper_berth': 0.0,
            'driving': 0.0,
            'on_duty_not_driving': 0.0,
        }
        for e in day_events:
            totals[e['status']] = round(totals[e['status']] + e['hours'], 4)

        # Round totals for clean output
        for k in totals:
            totals[k] = round(totals[k], 2)

        # Debug assertion: totals must sum to 24
        total_sum = sum(totals.values())
        assert abs(total_sum - HOURS_IN_DAY) < 0.02, \
            f"Day {day_number} totals sum to {total_sum}, expected {HOURS_IN_DAY}. Events: {day_events}"

        log = {
            'day': day_number,
            'date': _current_date(),
            'events': day_events,
            'totals': totals,
            'miles_today': round(miles_today, 1),
            'remarks': day_remarks,
        }
        daily_logs.append(log)

        # Reset for next day
        day_events = []
        day_remarks = []
        miles_today = 0.0

    def _start_new_day():
        """Start a new day after mandatory rest."""
        nonlocal day_number, current_time, driving_hours_today, window_start, hours_since_last_break, day_events, day_remarks

        day_number += 1
        current_time = 0.0  # Midnight

        # 10-hour mandatory off-duty rest
        last_location = daily_logs[-1]['events'][-2]['location'] if daily_logs else 'Unknown'
        day_events.append(_make_event(current_time, 'off_duty', last_location, MANDATORY_REST_HOURS))
        current_time += MANDATORY_REST_HOURS
        _add_remark(day_remarks, 0.0, last_location, 'Mandatory 10-hr rest')

        # Pre-trip inspection
        day_events.append(_make_event(current_time, 'on_duty_not_driving', last_location, PRE_POST_TRIP_HOURS))
        _add_remark(day_remarks, current_time, last_location, 'Pre-trip inspection')
        cycle_hours_used_add(PRE_POST_TRIP_HOURS)
        current_time += PRE_POST_TRIP_HOURS

        # Reset daily counters
        driving_hours_today = 0.0
        window_start = current_time - PRE_POST_TRIP_HOURS  # Window started at pre-trip
        hours_since_last_break = 0.0  # 10hr rest qualifies as break reset

    def cycle_hours_used_add(hours):
        """Track cycle hours."""
        nonlocal cycle_hours_used
        cycle_hours_used += hours

    def _do_34hr_restart(location):
        """
        Execute a 34-hour restart, splitting across calendar days.

        The restart is distributed as:
        1. Current day: finalized with off-duty padding (counts toward restart)
        2. Full 24hr off-duty day(s) if needed
        3. Final day: remaining restart hours as off-duty, then pre-trip inspection
        """
        nonlocal day_number, current_time, day_events, day_remarks, miles_today
        nonlocal driving_hours_today, window_start, hours_since_last_break, cycle_hours_used

        # Step 1: Finalize current day — the off-duty padding counts toward restart
        time_used_today = sum(e['hours'] for e in day_events)
        rest_in_current_day = max(0.0, HOURS_IN_DAY - time_used_today)
        _finalize_day()

        restart_remaining = RESTART_HOURS - rest_in_current_day

        # Step 2: Fill full off-duty days
        while restart_remaining >= HOURS_IN_DAY - 0.001:
            day_number += 1
            day_events = [_make_event(0.0, 'off_duty', location, HOURS_IN_DAY)]
            day_remarks = []
            _add_remark(day_remarks, 0.0, location, '34-hr restart (continued)')
            miles_today = 0.0  # Explicit reset
            _finalize_day()
            restart_remaining -= HOURS_IN_DAY

        # Step 3: Final restart day — partial off-duty, then pre-trip and resume
        day_number += 1
        current_time = 0.0
        day_events = []
        day_remarks = []

        if restart_remaining > 0.001:
            day_events.append(_make_event(0.0, 'off_duty', location, restart_remaining))
            _add_remark(day_remarks, 0.0, location, '34-hr restart (final)')
            current_time = restart_remaining

        # Pre-trip inspection
        day_events.append(_make_event(current_time, 'on_duty_not_driving', location, PRE_POST_TRIP_HOURS))
        _add_remark(day_remarks, current_time, location, 'Pre-trip inspection')
        current_time += PRE_POST_TRIP_HOURS

        # Reset ALL counters after 34-hr restart
        cycle_hours_used = PRE_POST_TRIP_HOURS  # Only the pre-trip counts
        driving_hours_today = 0.0
        window_start = current_time - PRE_POST_TRIP_HOURS
        hours_since_last_break = 0.0

    # ─── Trip Execution ──────────────────────────────────────────────

    # Day 1: Pre-trip inspection
    start_location = segments[0]['from_location'] if segments else 'Unknown'
    day_events.append(_make_event(current_time, 'on_duty_not_driving', start_location, PRE_POST_TRIP_HOURS))
    _add_remark(day_remarks, current_time, start_location, 'Pre-trip inspection')
    cycle_hours_used_add(PRE_POST_TRIP_HOURS)
    current_time += PRE_POST_TRIP_HOURS
    window_start = DEFAULT_START_HOUR  # Window starts at first on-duty

    # Process each segment
    for seg_idx, segment in enumerate(segments):
        seg_distance = segment['distance_miles']
        seg_from = segment['from_location']
        seg_to = segment['to_location']
        is_pickup = (seg_idx == 0)  # First segment ends at pickup
        # is_last = (seg_idx == len(segments) - 1)  # Last segment ends at dropoff

        # ── Zero-distance guard ──
        if seg_distance < 1:
            # No driving needed, but still log the stop
            if is_pickup:
                day_events.append(_make_event(current_time, 'on_duty_not_driving', seg_to, PICKUP_DROPOFF_HOURS))
                _add_remark(day_remarks, current_time, seg_to, 'Pickup (loading)')
                cycle_hours_used_add(PICKUP_DROPOFF_HOURS)
                current_time += PICKUP_DROPOFF_HOURS
                hours_since_last_break = 0.0  # Qualifying break >= 30min
            continue

        # ── Drive the segment ──
        remaining_drive_hours = seg_distance / DRIVER_SPEED_MPH
        remaining_miles = seg_distance
        current_drive_location = seg_from

        while remaining_drive_hours > 0.001:

            # ── Pre-drive check: 30-min break needed? ──
            if hours_since_last_break >= BREAK_THRESHOLD_HOURS - 0.001:
                # Must take a 30-min break before driving more
                day_events.append(_make_event(
                    current_time, 'off_duty',
                    current_drive_location, BREAK_DURATION_HOURS
                ))
                _add_remark(day_remarks, current_time, current_drive_location, '30-min break (8hr rule)')
                current_time += BREAK_DURATION_HOURS
                hours_since_last_break = 0.0

            # ── Pre-drive check: fuel stop needed? ──
            if miles_since_last_fuel >= FUEL_INTERVAL_MILES - 0.1:
                day_events.append(_make_event(
                    current_time, 'on_duty_not_driving',
                    current_drive_location, FUEL_STOP_HOURS
                ))
                _add_remark(day_remarks, current_time, current_drive_location, 'Fuel stop')
                cycle_hours_used_add(FUEL_STOP_HOURS)
                current_time += FUEL_STOP_HOURS
                miles_since_last_fuel = 0.0
                hours_since_last_break = 0.0  # Fuel stop >= 30min resets break counter

                # Record fuel stop for map
                stop_events.append({
                    'type': 'fuel',
                    'location_name': current_drive_location,
                    'total_miles_at_stop': round(total_miles_driven, 1),
                })

            # ── Calculate max driveable time ──
            miles_to_next_fuel = FUEL_INTERVAL_MILES - miles_since_last_fuel
            hours_to_next_fuel = miles_to_next_fuel / DRIVER_SPEED_MPH

            max_drive = min(
                remaining_drive_hours,
                MAX_DRIVING_HOURS - driving_hours_today,               # 11hr limit
                _window_remaining(),                                    # 14hr window
                BREAK_THRESHOLD_HOURS - hours_since_last_break,         # 8hr break rule
                hours_to_next_fuel,                                     # fuel stop split
                max(0.0, MAX_CYCLE_HOURS - cycle_hours_used),           # 70hr cycle limit
                _hours_remaining_in_day(),                              # midnight boundary
            )

            # Clamp to positive
            max_drive = max(0.0, max_drive)

            if max_drive > 0.001:
                # Log driving event
                drive_miles = max_drive * DRIVER_SPEED_MPH
                day_events.append(_make_event(current_time, 'driving', current_drive_location, max_drive, drive_miles))

                if abs(max_drive - remaining_drive_hours) < 0.01:
                    # This is the last chunk — we'll arrive at destination
                    _add_remark(day_remarks, current_time, current_drive_location, f'Driving to {seg_to}')
                else:
                    _add_remark(day_remarks, current_time, current_drive_location, 'Driving')

                # Update state
                current_time += max_drive
                driving_hours_today += max_drive
                hours_since_last_break += max_drive
                cycle_hours_used_add(max_drive)
                miles_since_last_fuel += drive_miles
                miles_today += drive_miles
                total_miles_driven += drive_miles
                remaining_drive_hours -= max_drive
                remaining_miles -= drive_miles

            # ── Post-drive checks ──

            # Check 0: Midnight boundary — need to split into next calendar day
            if current_time >= HOURS_IN_DAY - 0.001 and remaining_drive_hours > 0.001:
                # Day is full, finalize and start new day
                _finalize_day()
                _start_new_day()
                continue

            # Check 1: Cycle exhausted (70 hours) → 34-hour restart
            if cycle_hours_used >= MAX_CYCLE_HOURS - 0.001 and remaining_drive_hours > 0.001:
                # Post-trip inspection
                day_events.append(_make_event(
                    current_time, 'on_duty_not_driving',
                    current_drive_location, PRE_POST_TRIP_HOURS
                ))
                _add_remark(day_remarks, current_time, current_drive_location, 'Post-trip inspection')
                cycle_hours_used_add(PRE_POST_TRIP_HOURS)
                current_time += PRE_POST_TRIP_HOURS

                # Record rest stop for map
                stop_events.append({
                    'type': 'rest',
                    'location_name': current_drive_location,
                    'total_miles_at_stop': round(total_miles_driven, 1),
                })

                # Execute 34-hour restart
                _do_34hr_restart(current_drive_location)
                continue  # Loop back to drive remaining miles

            # Check 2: Day needs to end (11hr or 14hr limit hit)
            needs_day_end = (
                driving_hours_today >= MAX_DRIVING_HOURS - 0.001 or
                _window_remaining() < 0.001
            )

            if needs_day_end and remaining_drive_hours > 0.001:
                # Still have driving left — must rest and continue tomorrow

                # Post-trip inspection
                day_events.append(_make_event(
                    current_time, 'on_duty_not_driving',
                    current_drive_location, PRE_POST_TRIP_HOURS
                ))
                _add_remark(day_remarks, current_time, current_drive_location, 'Post-trip inspection')
                cycle_hours_used_add(PRE_POST_TRIP_HOURS)
                current_time += PRE_POST_TRIP_HOURS

                # Record rest stop for map
                stop_events.append({
                    'type': 'rest',
                    'location_name': current_drive_location,
                    'total_miles_at_stop': round(total_miles_driven, 1),
                })

                # Finalize the day
                _finalize_day()

                # Start new day
                _start_new_day()

            elif max_drive < 0.001 and not needs_day_end:
                # Safety valve: max_drive is 0 but no check triggered
                # This shouldn't happen normally but guards against infinite loops
                break

        # ── Arrived at segment destination ──

        if is_pickup:
            # Pickup stop: 1 hour OND
            day_events.append(_make_event(current_time, 'on_duty_not_driving', seg_to, PICKUP_DROPOFF_HOURS))
            _add_remark(day_remarks, current_time, seg_to, 'Pickup (loading)')
            cycle_hours_used_add(PICKUP_DROPOFF_HOURS)
            current_time += PICKUP_DROPOFF_HOURS
            hours_since_last_break = 0.0  # Qualifying break >= 30min

    # ── At dropoff: 1hr OND + 30min post-trip ──
    dropoff_location = segments[-1]['to_location'] if segments else 'Unknown'

    day_events.append(_make_event(current_time, 'on_duty_not_driving', dropoff_location, PICKUP_DROPOFF_HOURS))
    _add_remark(day_remarks, current_time, dropoff_location, 'Dropoff (unloading)')
    cycle_hours_used_add(PICKUP_DROPOFF_HOURS)
    current_time += PICKUP_DROPOFF_HOURS

    day_events.append(_make_event(current_time, 'on_duty_not_driving', dropoff_location, PRE_POST_TRIP_HOURS))
    _add_remark(day_remarks, current_time, dropoff_location, 'Post-trip inspection')
    cycle_hours_used_add(PRE_POST_TRIP_HOURS)
    current_time += PRE_POST_TRIP_HOURS

    # ── Finalize the last day ──
    _finalize_day()

    return {
        'daily_logs': daily_logs,
        'stop_events': stop_events,
    }

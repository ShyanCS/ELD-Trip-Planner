import { describe, expect, it } from 'vitest';
import { buildSegments, parseTime, STATUS_ROWS } from '../logSheetDraw';

describe('parseTime', () => {
  it('parses HH:MM to decimal hours', () => {
    expect(parseTime('08:30')).toBe(8.5);
    expect(parseTime('13:45')).toBeCloseTo(13.75, 5);
    expect(parseTime('00:00')).toBe(0);
  });

  it('returns 0 for invalid input', () => {
    expect(parseTime(null)).toBe(0);
    expect(parseTime(undefined)).toBe(0);
    expect(parseTime(123)).toBe(0);
    expect(parseTime('')).toBe(0);
  });
});

describe('buildSegments', () => {
  it('returns a full off-duty day when there are no events', () => {
    const segments = buildSegments([]);
    expect(segments).toEqual([{ startHour: 0, endHour: 24, status: 'off_duty', rowIndex: 0 }]);
  });

  it('fills gaps before, between, and after events with off-duty', () => {
    const segments = buildSegments([
      { time: '06:00', hours: 4, status: 'driving' },
      { time: '12:00', hours: 1, status: 'on_duty_not_driving' },
    ]);

    // Off-duty 0→6, driving 6→10, off-duty gap 10→12, on-duty 12→13, off-duty 13→24
    expect(segments.map((s) => [s.startHour, s.endHour, s.status])).toEqual([
      [0, 6, 'off_duty'],
      [6, 10, 'driving'],
      [10, 12, 'off_duty'],
      [12, 13, 'on_duty_not_driving'],
      [13, 24, 'off_duty'],
    ]);
  });

  it('clamps events that run past midnight at hour 24', () => {
    const segments = buildSegments([{ time: '22:00', hours: 5, status: 'sleeper_berth' }]);
    const last = segments[segments.length - 1];
    expect(last.endHour).toBe(24);
    expect(last.status).toBe('sleeper_berth');
  });

  it('maps statuses to their grid row index and skips unknown ones', () => {
    const segments = buildSegments([
      { time: '08:00', hours: 1, status: 'not_a_status' },
      { time: '09:00', hours: 1, status: 'driving' },
    ]);

    const driving = segments.find((s) => s.status === 'driving');
    expect(driving.rowIndex).toBe(STATUS_ROWS.indexOf('driving'));
    expect(segments.some((s) => s.status === 'not_a_status')).toBe(false);
    // The unknown-status event leaves a gap that is filled as off-duty
    expect(segments.some((s) => s.status === 'off_duty' && s.endHour <= 9)).toBe(true);
  });
});

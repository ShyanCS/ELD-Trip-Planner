import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import TripTimeline from '../TripTimeline';
import MOCK_TRIP_RESULT from '../../api/mockTripResult';

const MOCK_DAILY_LOGS = MOCK_TRIP_RESULT.daily_logs;

describe('TripTimeline', () => {
  it('returns null when dailyLogs is undefined', () => {
    const { container } = render(<TripTimeline dailyLogs={undefined} />);
    expect(container.firstChild).toBeNull();
  });

  it('returns null when dailyLogs is an empty array', () => {
    const { container } = render(<TripTimeline dailyLogs={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders a timeline wrapper when logs are provided', () => {
    const { container } = render(<TripTimeline dailyLogs={MOCK_DAILY_LOGS} />);
    expect(container.querySelector('.trip-timeline')).toBeInTheDocument();
  });

  it('renders one timeline-day block per daily log', () => {
    const { container } = render(<TripTimeline dailyLogs={MOCK_DAILY_LOGS} />);
    const dayBlocks = container.querySelectorAll('.timeline-day');
    expect(dayBlocks).toHaveLength(MOCK_DAILY_LOGS.length);
  });

  it('renders "Day 1", "Day 2" etc. headings', () => {
    render(<TripTimeline dailyLogs={MOCK_DAILY_LOGS} />);
    expect(screen.getByText('Day 1')).toBeInTheDocument();
    if (MOCK_DAILY_LOGS.length >= 2) {
      expect(screen.getByText('Day 2')).toBeInTheDocument();
    }
  });

  it('renders the date for each day', () => {
    render(<TripTimeline dailyLogs={MOCK_DAILY_LOGS} />);
    const firstDate = MOCK_DAILY_LOGS[0].date;
    expect(screen.getByText(new RegExp(firstDate))).toBeInTheDocument();
  });

  it('renders timeline events (remarks) for each day', () => {
    const { container } = render(<TripTimeline dailyLogs={MOCK_DAILY_LOGS} />);
    const events = container.querySelectorAll('.timeline-event');
    const totalRemarks = MOCK_DAILY_LOGS.reduce((acc, d) => acc + d.remarks.length, 0);
    expect(events).toHaveLength(totalRemarks);
  });

  it('applies pickup CSS class for pickup remarks', () => {
    const logsWithPickup = [
      {
        day: 1,
        date: '2026-05-07',
        miles_today: 0,
        remarks: ['08:30 Kansas City, MO - Pickup (loading)'],
      },
    ];
    const { container } = render(<TripTimeline dailyLogs={logsWithPickup} />);
    expect(container.querySelector('.timeline-event__dot--pickup')).toBeInTheDocument();
  });

  it('applies dropoff CSS class for dropoff remarks', () => {
    const logsWithDropoff = [
      {
        day: 1,
        date: '2026-05-07',
        miles_today: 0,
        remarks: ['16:00 Los Angeles, CA - Dropoff (unloading)'],
      },
    ];
    const { container } = render(<TripTimeline dailyLogs={logsWithDropoff} />);
    expect(container.querySelector('.timeline-event__dot--dropoff')).toBeInTheDocument();
  });

  it('applies rest CSS class for break remarks', () => {
    const logsWithRest = [
      {
        day: 1,
        date: '2026-05-07',
        miles_today: 0,
        remarks: ['12:00 Somewhere, KS - 30-min break (HOS)'],
      },
    ];
    const { container } = render(<TripTimeline dailyLogs={logsWithRest} />);
    expect(container.querySelector('.timeline-event__dot--rest')).toBeInTheDocument();
  });

  it('parses remark time correctly (HH:MM format)', () => {
    const logsWithTime = [
      {
        day: 1,
        date: '2026-05-07',
        miles_today: 0,
        remarks: ['09:30 Chicago, IL - Pre-trip inspection'],
      },
    ];
    render(<TripTimeline dailyLogs={logsWithTime} />);
    expect(screen.getByText('09:30')).toBeInTheDocument();
  });
});

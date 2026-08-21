import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import TripSummary from '../TripSummary';
import MOCK_TRIP_RESULT from '../../api/mockTripResult';

const MOCK_ROUTE = MOCK_TRIP_RESULT.route;
const MOCK_DAILY_LOGS = MOCK_TRIP_RESULT.daily_logs;
const MOCK_STOP_EVENTS = MOCK_TRIP_RESULT.stop_events;

function renderSummary(overrides = {}) {
  const props = {
    route: MOCK_ROUTE,
    dailyLogs: MOCK_DAILY_LOGS,
    stopEvents: MOCK_STOP_EVENTS,
    onReset: vi.fn(),
    ...overrides,
  };
  return render(<TripSummary {...props} />);
}

describe('TripSummary', () => {
  it('renders without throwing', () => {
    expect(() => renderSummary()).not.toThrow();
  });

  it('displays the total distance from route data', () => {
    renderSummary();
    // "1,745.3" formatted via toLocaleString
    expect(screen.getByText(/1[,.]745/)).toBeInTheDocument();
  });

  it('displays the estimated drive time from route data', () => {
    renderSummary();
    expect(screen.getByText(/31\.7/)).toBeInTheDocument();
  });

  it('shows the correct number of days', () => {
    renderSummary();
    const days = MOCK_DAILY_LOGS.length;
    // Scope to the specific stat card to avoid collision when stop count equals day count
    const card = document.getElementById('stat-days');
    expect(within(card).getByText(String(days))).toBeInTheDocument();
  });

  it('shows total stop count', () => {
    renderSummary();
    const totalStops = MOCK_STOP_EVENTS.length;
    // Scope to the stops stat card to avoid collision with days count
    const card = document.getElementById('stat-stops');
    expect(within(card).getByText(String(totalStops))).toBeInTheDocument();
  });

  it('renders fuel and rest stop tags when present', () => {
    renderSummary();
    const fuelCount = MOCK_STOP_EVENTS.filter((s) => s.type === 'fuel').length;
    const restCount = MOCK_STOP_EVENTS.filter((s) => s.type === 'rest').length;

    if (fuelCount > 0) {
      expect(screen.getByText(new RegExp(`${fuelCount} fuel`))).toBeInTheDocument();
    }
    if (restCount > 0) {
      expect(screen.getByText(new RegExp(`${restCount} rest`))).toBeInTheDocument();
    }
  });

  it('renders "Plan Another Trip" button', () => {
    renderSummary();
    expect(screen.getByRole('button', { name: /plan another trip/i })).toBeInTheDocument();
  });

  it('calls onReset when "Plan Another Trip" is clicked', () => {
    const onReset = vi.fn();
    renderSummary({ onReset });

    screen.getByRole('button', { name: /plan another trip/i }).click();
    expect(onReset).toHaveBeenCalledOnce();
  });
});

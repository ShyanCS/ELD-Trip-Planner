import { describe, it, expect, vi, beforeAll } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

// ─── Mock child components that need canvas / leaflet ────────────────────────
vi.mock('./components/MapView', () => ({
  default: () => <div data-testid="map-view" />,
}));
vi.mock('./components/LogSheet', () => ({
  default: ({ log }) => <div data-testid="log-sheet">{log.day}</div>,
}));
vi.mock('./components/ExportPdfButton', () => ({
  default: () => <button data-testid="export-pdf">Export PDF</button>,
}));

// ─── Mock tripApi ─────────────────────────────────────────────────────────────
vi.mock('./api/tripApi', () => ({
  planTrip: vi.fn(),
}));

import { planTrip } from './api/tripApi';
import MOCK_TRIP_RESULT from './api/mockTripResult';

// ─── Import App after mocks ────────────────────────────────────────────────────
let App;
beforeAll(async () => {
  const mod = await import('./App');
  App = mod.default;
});

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('App', () => {
  function fillAndSubmitForm() {
    fireEvent.change(screen.getByLabelText(/current location/i), {
      target: { value: 'Chicago, IL' },
    });
    fireEvent.change(screen.getByLabelText(/pickup location/i), {
      target: { value: 'Kansas City, MO' },
    });
    fireEvent.change(screen.getByLabelText(/dropoff location/i), {
      target: { value: 'Los Angeles, CA' },
    });
    fireEvent.change(screen.getByLabelText(/cycle hours used/i), {
      target: { value: '20' },
    });
    fireEvent.click(screen.getByRole('button', { name: /plan trip/i }));
  }

  it('renders the header title', () => {
    render(<App />);
    expect(screen.getByRole('heading', { name: /ELD Trip Planner/i })).toBeInTheDocument();
  });

  it('renders the TripForm on initial load', () => {
    render(<App />);
    expect(screen.getByRole('button', { name: /plan trip/i })).toBeInTheDocument();
  });

  it('shows results after a successful planTrip call', async () => {
    planTrip.mockResolvedValueOnce(MOCK_TRIP_RESULT);
    render(<App />);
    fillAndSubmitForm();

    await waitFor(() => {
      // TripSummary should appear (contains total distance text)
      expect(screen.getByTestId('map-view')).toBeInTheDocument();
    });
  });

  it('shows log sheets for each day in the result', async () => {
    planTrip.mockResolvedValueOnce(MOCK_TRIP_RESULT);
    render(<App />);
    fillAndSubmitForm();

    await waitFor(() => {
      const sheets = screen.getAllByTestId('log-sheet');
      expect(sheets.length).toBe(MOCK_TRIP_RESULT.daily_logs.length);
    });
  });

  it('shows an error banner when planTrip rejects with a server error', async () => {
    planTrip.mockRejectedValueOnce({
      response: { data: { error: 'ORS route not found' } },
    });
    render(<App />);
    fillAndSubmitForm();

    await waitFor(() => {
      expect(screen.getByText(/ORS route not found/i)).toBeInTheDocument();
    });
  });

  it('shows a timeout message when request times out', async () => {
    planTrip.mockRejectedValueOnce({ code: 'ECONNABORTED' });
    render(<App />);
    fillAndSubmitForm();

    await waitFor(() => {
      expect(screen.getByText(/request timed out/i)).toBeInTheDocument();
    });
  });

  it('shows a cannot-reach-server message when there is no response', async () => {
    planTrip.mockRejectedValueOnce({});
    render(<App />);
    fillAndSubmitForm();

    await waitFor(() => {
      expect(screen.getByText(/cannot reach the server/i)).toBeInTheDocument();
    });
  });

  it('dismissing the error clears it from the banner', async () => {
    planTrip.mockRejectedValueOnce({
      response: { data: { error: 'Some error' } },
    });
    render(<App />);
    fillAndSubmitForm();

    await waitFor(() => screen.getByText(/some error/i));

    // The ErrorBanner has a dismiss button
    const dismiss = screen.getByRole('button', { name: /dismiss error/i });
    fireEvent.click(dismiss);

    expect(screen.queryByText(/some error/i)).not.toBeInTheDocument();
  });
});

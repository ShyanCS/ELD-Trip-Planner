import { describe, it, expect, beforeAll } from 'vitest';
import { render, screen } from '@testing-library/react';
import LogSheet from '../LogSheet';
import MOCK_TRIP_RESULT from '../../api/mockTripResult';

// Canvas is not implemented in jsdom — mock the context methods so
// LogSheet's useEffect doesn't throw when it tries to draw.
beforeAll(() => {
  HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
    scale: vi.fn(),
    clearRect: vi.fn(),
    fillRect: vi.fn(),
    fillText: vi.fn(),
    strokeRect: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    setLineDash: vi.fn(),
    save: vi.fn(),
    restore: vi.fn(),
    translate: vi.fn(),
    rotate: vi.fn(),
    arc: vi.fn(),
    fill: vi.fn(),
    measureText: vi.fn(() => ({ width: 50 })),
    createLinearGradient: vi.fn(() => ({
      addColorStop: vi.fn(),
    })),
  }));
});

// Use the first daily log from the mock data
const MOCK_LOG = MOCK_TRIP_RESULT.daily_logs[0];

describe('LogSheet', () => {
  it('renders a canvas element', () => {
    const { container } = render(<LogSheet log={MOCK_LOG} />);
    const canvas = container.querySelector('canvas');
    expect(canvas).toBeInTheDocument();
  });

  it('renders without throwing given a valid log from mock data', () => {
    expect(() => render(<LogSheet log={MOCK_LOG} />)).not.toThrow();
  });

  it('renders a canvas for each daily log in mock data', () => {
    MOCK_TRIP_RESULT.daily_logs.forEach((log) => {
      const { container, unmount } = render(<LogSheet log={log} />);
      expect(container.querySelector('canvas')).toBeInTheDocument();
      unmount();
    });
  });
});

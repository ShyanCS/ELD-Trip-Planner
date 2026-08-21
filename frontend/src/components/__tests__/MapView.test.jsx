import { describe, it, expect, vi, beforeAll } from 'vitest';
import { render, screen } from '@testing-library/react';
import MOCK_TRIP_RESULT from '../../api/mockTripResult';

// ─── Mock react-leaflet (no DOM canvas available in jsdom) ───────────────────
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }) => <div data-testid="map-container">{children}</div>,
  TileLayer: () => <div data-testid="tile-layer" />,
  Polyline: ({ positions }) => (
    <div data-testid="polyline" data-positions={JSON.stringify(positions)} />
  ),
  Marker: ({ children, position }) => (
    <div data-testid="marker" data-position={JSON.stringify(position)}>
      {children}
    </div>
  ),
  Popup: ({ children }) => <div data-testid="popup">{children}</div>,
  useMap: () => ({
    fitBounds: vi.fn(),
  }),
}));

// ─── Mock leaflet (icon construction) ────────────────────────────────────────
vi.mock('leaflet', () => ({
  default: {
    Icon: {
      Default: {
        prototype: { _getIconUrl: vi.fn() },
        mergeOptions: vi.fn(),
      },
    },
    divIcon: vi.fn(() => ({})),
    latLngBounds: vi.fn(() => ({
      pad: vi.fn(),
    })),
  },
  divIcon: vi.fn(() => ({})),
  latLngBounds: vi.fn(() => ({})),
  Icon: {
    Default: {
      prototype: { _getIconUrl: vi.fn() },
      mergeOptions: vi.fn(),
    },
  },
}));

// ─── Import component AFTER mocks are set up ─────────────────────────────────
let MapView;
beforeAll(async () => {
  const mod = await import('../MapView');
  MapView = mod.default;
});

const MOCK_GEOMETRY = MOCK_TRIP_RESULT.route.geometry;
const MOCK_WAYPOINTS = MOCK_TRIP_RESULT.route.waypoints;

describe('MapView', () => {
  it('returns null when geometry has no coordinates', () => {
    const { container } = render(
      <MapView geometry={{ type: 'LineString', coordinates: [] }} waypoints={[]} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders the map container when coordinates are provided', () => {
    render(<MapView geometry={MOCK_GEOMETRY} waypoints={MOCK_WAYPOINTS} />);
    expect(screen.getByTestId('map-container')).toBeInTheDocument();
  });

  it('renders the tile layer', () => {
    render(<MapView geometry={MOCK_GEOMETRY} waypoints={MOCK_WAYPOINTS} />);
    expect(screen.getByTestId('tile-layer')).toBeInTheDocument();
  });

  it('renders the route polyline', () => {
    render(<MapView geometry={MOCK_GEOMETRY} waypoints={MOCK_WAYPOINTS} />);
    expect(screen.getByTestId('polyline')).toBeInTheDocument();
  });

  it('passes [lat, lon] pairs to Polyline (converts from GeoJSON [lon, lat])', () => {
    render(<MapView geometry={MOCK_GEOMETRY} waypoints={[]} />);
    const polyline = screen.getByTestId('polyline');
    const positions = JSON.parse(polyline.dataset.positions);
    // First coord in geometry is [-87.6298, 41.8781] (lon, lat)
    // Leaflet needs [lat, lon] → [41.8781, -87.6298]
    expect(positions[0][0]).toBeCloseTo(41.8781, 3);
    expect(positions[0][1]).toBeCloseTo(-87.6298, 3);
  });

  it('renders a Marker for each waypoint', () => {
    render(<MapView geometry={MOCK_GEOMETRY} waypoints={MOCK_WAYPOINTS} />);
    const markers = screen.getAllByTestId('marker');
    expect(markers).toHaveLength(MOCK_WAYPOINTS.length);
  });

  it('renders the map legend with all waypoint types', () => {
    const { container } = render(<MapView geometry={MOCK_GEOMETRY} waypoints={MOCK_WAYPOINTS} />);
    const legendItems = container.querySelectorAll('.map-legend__item');
    // Start, Pickup, Dropoff, Fuel, Rest = 5 legend items
    expect(legendItems.length).toBeGreaterThanOrEqual(5);
  });

  it('renders popup text for each waypoint', () => {
    const singleWaypoint = [{ type: 'start', name: 'Chicago, IL', lat: 41.88, lon: -87.63, miles_from_start: 0 }];
    render(<MapView geometry={MOCK_GEOMETRY} waypoints={singleWaypoint} />);
    expect(screen.getByText('Chicago, IL')).toBeInTheDocument();
  });

  it('renders with id="map-view" on the root div', () => {
    render(<MapView geometry={MOCK_GEOMETRY} waypoints={MOCK_WAYPOINTS} />);
    expect(document.getElementById('map-view')).toBeInTheDocument();
  });
});

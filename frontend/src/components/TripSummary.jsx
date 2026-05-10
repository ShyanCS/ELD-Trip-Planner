import './TripSummary.css';

/**
 * TripSummary — 4 stat cards showing trip overview.
 *
 * Props:
 *   route      — { total_distance_miles, total_duration_hours }
 *   dailyLogs  — array of daily log objects
 *   stopEvents — array of stop event objects
 *   onReset    — callback to go back to the form
 */
export default function TripSummary({ route, dailyLogs, stopEvents, onReset }) {
  const fuelStops = stopEvents.filter((s) => s.type === 'fuel').length;
  const restStops = stopEvents.filter((s) => s.type === 'rest').length;

  return (
    <div className="trip-summary" id="trip-summary">
      {/* Header */}
      <div className="trip-summary__header">
        <h2>Trip Plan Ready</h2>
        <button className="btn btn--secondary" onClick={onReset} id="plan-another">
          ← Plan Another Trip
        </button>
      </div>

      {/* Stat Cards */}
      <div className="stat-cards-grid">
        <div className="stat-card" id="stat-distance">
          <div className="stat-card__label">Total Distance</div>
          <div className="stat-card__value">
            {route.total_distance_miles.toLocaleString()}
            <span className="stat-card__unit">mi</span>
          </div>
        </div>

        <div className="stat-card" id="stat-duration">
          <div className="stat-card__label">Est. Drive Time</div>
          <div className="stat-card__value">
            {route.total_duration_hours.toFixed(1)}
            <span className="stat-card__unit">hrs</span>
          </div>
        </div>

        <div className="stat-card" id="stat-days">
          <div className="stat-card__label">Days Required</div>
          <div className="stat-card__value">
            {dailyLogs.length}
            <span className="stat-card__unit">{dailyLogs.length === 1 ? 'day' : 'days'}</span>
          </div>
        </div>

        <div className="stat-card" id="stat-stops">
          <div className="stat-card__label">Stops</div>
          <div className="stat-card__value">
            {stopEvents.length}
            <span className="stat-card__unit">total</span>
          </div>
          <div className="stat-card__detail">
            {fuelStops > 0 && <span className="stat-card__tag stat-card__tag--fuel">{fuelStops} fuel</span>}
            {restStops > 0 && <span className="stat-card__tag stat-card__tag--rest">{restStops} rest</span>}
          </div>
        </div>
      </div>
    </div>
  );
}

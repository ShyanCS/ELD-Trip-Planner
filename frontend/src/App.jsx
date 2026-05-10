import { useState } from 'react';
import TripForm from './components/TripForm';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorBanner from './components/ErrorBanner';
import TripSummary from './components/TripSummary';
import TripTimeline from './components/TripTimeline';
import MapView from './components/MapView';
import LogSheet from './components/LogSheet';
import ExportPdfButton from './components/ExportPdfButton';
import { planTrip } from './api/tripApi';
import './App.css';

function App() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [tripResult, setTripResult] = useState(null);

  const handleSubmit = async (formData) => {
    setIsLoading(true);
    setError('');
    setTripResult(null);

    try {
      const result = await planTrip(formData);
      setTripResult(result);
    } catch (err) {
      // Extract the best error message
      if (err.response?.data?.error) {
        setError(err.response.data.error);
      } else if (err.response?.data?.details) {
        // Validation errors from DRF — flatten them
        const details = err.response.data.details;
        const messages = Object.entries(details)
          .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
          .join(' · ');
        setError(messages);
      } else if (err.code === 'ECONNABORTED') {
        setError('Request timed out. The server may be overloaded — please try again.');
      } else if (!err.response) {
        setError('Cannot reach the server. Make sure the backend is running on port 8000.');
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setTripResult(null);
    setError('');
  };

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="app-header">
        <div className="container app-header__inner">
          <div className="app-header__brand">
            <div className="app-header__logo">
              <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="2" y="6" width="24" height="16" rx="1" stroke="var(--accent-primary)" strokeWidth="1.5" fill="none"/>
                <circle cx="9" cy="22" r="2.5" stroke="var(--accent-primary)" strokeWidth="1.5" fill="none"/>
                <circle cx="19" cy="22" r="2.5" stroke="var(--accent-primary)" strokeWidth="1.5" fill="none"/>
                <line x1="6" y1="10" x2="22" y2="10" stroke="var(--accent-primary)" strokeWidth="1" opacity="0.5"/>
                <line x1="6" y1="14" x2="22" y2="14" stroke="var(--accent-primary)" strokeWidth="1" opacity="0.5"/>
                <line x1="6" y1="18" x2="22" y2="18" stroke="var(--accent-primary)" strokeWidth="1" opacity="0.5"/>
              </svg>
            </div>
            <div className="app-header__title-block">
              <h1 className="app-header__title">ELD Trip Planner</h1>
              <span className="app-header__subtitle">FMCSA Hours of Service Compliance</span>
            </div>
          </div>

          <div className="app-header__badge">
            <span className="status-dot status-dot--driving"></span>
            <span>HOS Engine v1.0</span>
          </div>
        </div>
      </header>

      {/* ── Main Content ── */}
      <main className="app-main">
        <div className="container">

          {/* Error Banner */}
          <ErrorBanner message={error} onDismiss={() => setError('')} />

          {/* Show form when no results */}
          {!tripResult ? (
            <>
              <div className="app-hero">
                <h2>Plan Your Next Trip</h2>
                <p>
                  Enter your route details below. The HOS compliance engine will generate
                  FMCSA-compliant daily log sheets, calculate mandatory breaks and fuel stops,
                  and plot your route on the map.
                </p>
              </div>

              <TripForm onSubmit={handleSubmit} isLoading={isLoading} />

              {isLoading && <LoadingSpinner />}
            </>
          ) : (
            <>
              <TripSummary
                route={tripResult.route}
                dailyLogs={tripResult.daily_logs}
                stopEvents={tripResult.stop_events}
                onReset={handleReset}
              />

              {/* Trip Timeline */}
              <div className="section-header">
                <h3>Trip Timeline</h3>
              </div>
              <TripTimeline dailyLogs={tripResult.daily_logs} />

              {/* Route Map */}
              <div className="section-header">
                <h3>Route Map</h3>
              </div>
              <MapView
                geometry={tripResult.route.geometry}
                waypoints={tripResult.route.waypoints}
              />

              {/* Daily Log Sheets */}
              <div className="results-logs">
                <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3>Daily Log Sheets</h3>
                  <ExportPdfButton />
                </div>
                {tripResult.daily_logs.map((log) => (
                  <LogSheet key={log.day} log={log} />
                ))}
              </div>
            </>
          )}
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="app-footer">
        <div className="container app-footer__inner">
          <span className="app-footer__text">
            ELD Trip Planner — Property-carrying CMV · 11hr drive · 14hr window · 70hr cycle
          </span>
        </div>
      </footer>
    </div>
  );
}

export default App;

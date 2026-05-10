import './LoadingSpinner.css';

/**
 * LoadingSpinner — pulsing dots animation (not a rotating spinner).
 *
 * Props:
 *   message — optional loading message
 */
export default function LoadingSpinner({ message = 'Calculating HOS-compliant route…' }) {
  return (
    <div className="loading-container" id="loading-spinner">
      <div className="loading-dots">
        <span></span>
        <span></span>
        <span></span>
      </div>
      {message && <p className="loading-message">{message}</p>}
    </div>
  );
}

/**
 * ErrorBanner — dismissible red error banner.
 *
 * Props:
 *   message   — error message string
 *   onDismiss — callback to clear the error
 */
export default function ErrorBanner({ message, onDismiss }) {
  if (!message) return null;

  return (
    <div className="error-banner" id="error-banner" role="alert">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5"/>
        <line x1="8" y1="4.5" x2="8" y2="9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        <circle cx="8" cy="11.5" r="0.75" fill="currentColor"/>
      </svg>
      <span>{message}</span>
      <button onClick={onDismiss} aria-label="Dismiss error" id="dismiss-error">
        ×
      </button>
    </div>
  );
}

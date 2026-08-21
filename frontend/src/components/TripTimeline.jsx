import './TripTimeline.css';

/**
 * TripTimeline Component
 * Renders a vertical timeline summarizing the daily logs and remarks.
 * 
 * Props:
 *   dailyLogs: Array of daily log objects (from /api/trip/plan/)
 */
export default function TripTimeline({ dailyLogs }) {
  if (!dailyLogs || dailyLogs.length === 0) return null;

  return (
    <div className="trip-timeline">
      {dailyLogs.map((log) => (
        <div key={log.day} className="timeline-day">
          <div className="timeline-day__header">
            <h4>Day {log.day}</h4>
            <span className="timeline-day__meta">
              {log.date} • {log.miles_today} miles
            </span>
          </div>

          <div className="timeline-events">
            {log.remarks.map((remark, idx) => {
              // Parse the remark. Expected format: "HH:MM Location - Description"
              const match = remark.match(/^(\d{2}:\d{2})\s+([^-]+)\s+-\s+(.+)$/);
              let time = '';
              let location = '';
              let description = remark;

              if (match) {
                time = match[1];
                location = match[2].trim();
                description = match[3].trim();
              }

              // Determine event type for styling
              const isRest = description.toLowerCase().includes('break');
              const _isPreTrip = description.toLowerCase().includes('pre-trip');
              const _isPostTrip = description.toLowerCase().includes('post-trip');
              const isPickup = description.toLowerCase().includes('pickup');
              const isDropoff = description.toLowerCase().includes('dropoff');
              const _isDriving = description.toLowerCase().includes('driving');
              
              let eventClass = 'timeline-event__dot--default';
              if (isRest) eventClass = 'timeline-event__dot--rest';
              if (isPickup) eventClass = 'timeline-event__dot--pickup';
              if (isDropoff) eventClass = 'timeline-event__dot--dropoff';

              return (
                <div key={idx} className="timeline-event">
                  <div className="timeline-event__time">{time}</div>
                  <div className="timeline-event__node">
                    <div className={`timeline-event__dot ${eventClass}`}></div>
                    {/* The line is drawn via CSS border on the node container */}
                  </div>
                  <div className="timeline-event__content">
                    <div className="timeline-event__location">{location}</div>
                    <div className="timeline-event__description">{description}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

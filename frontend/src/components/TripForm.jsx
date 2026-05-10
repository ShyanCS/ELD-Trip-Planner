import { useState } from 'react';
import './TripForm.css';

/**
 * TripForm — 5-field input form for trip planning.
 *
 * Props:
 *   onSubmit(formData)  — called with validated form data
 *   isLoading           — disables form when true
 */
export default function TripForm({ onSubmit, isLoading }) {
  const [formData, setFormData] = useState({
    current_location: '',
    pickup_location: '',
    dropoff_location: '',
    current_cycle_used: '',
    start_date: '',
  });

  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    // Clear error on change
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  const handleBlur = (e) => {
    const { name } = e.target;
    setTouched((prev) => ({ ...prev, [name]: true }));
    validateField(name, formData[name]);
  };

  const validateField = (name, value) => {
    let error = '';

    switch (name) {
      case 'current_location':
        if (!value.trim()) error = 'Current location is required.';
        break;
      case 'pickup_location':
        if (!value.trim()) error = 'Pickup location is required.';
        break;
      case 'dropoff_location':
        if (!value.trim()) error = 'Dropoff location is required.';
        break;
      case 'current_cycle_used': {
        const num = parseFloat(value);
        if (value === '' || isNaN(num)) {
          error = 'Cycle hours are required.';
        } else if (num < 0) {
          error = 'Cannot be negative.';
        } else if (num > 70) {
          error = 'Cannot exceed 70 hours.';
        }
        break;
      }
      default:
        break;
    }

    setErrors((prev) => ({ ...prev, [name]: error }));
    return error;
  };

  const validateAll = () => {
    const newErrors = {};
    let hasError = false;

    ['current_location', 'pickup_location', 'dropoff_location', 'current_cycle_used'].forEach(
      (field) => {
        const error = validateField(field, formData[field]);
        if (error) {
          newErrors[field] = error;
          hasError = true;
        }
      }
    );

    // Mark all as touched
    setTouched({
      current_location: true,
      pickup_location: true,
      dropoff_location: true,
      current_cycle_used: true,
    });

    setErrors(newErrors);
    return !hasError;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validateAll()) return;

    // Build the payload
    const payload = {
      current_location: formData.current_location.trim(),
      pickup_location: formData.pickup_location.trim(),
      dropoff_location: formData.dropoff_location.trim(),
      current_cycle_used: parseFloat(formData.current_cycle_used),
    };

    if (formData.start_date) {
      payload.start_date = formData.start_date;
    }

    onSubmit(payload);
  };

  const fieldClass = (name) =>
    touched[name] && errors[name] ? 'input--error' : '';

  return (
    <form className="trip-form" onSubmit={handleSubmit} id="trip-plan-form">
      <div className="trip-form__header">
        <h3>Route Details</h3>
      </div>

      <div className="trip-form__grid">
        {/* Current Location */}
        <div className="input-group" id="field-current-location">
          <label htmlFor="current_location">Current Location</label>
          <input
            type="text"
            id="current_location"
            name="current_location"
            placeholder="e.g. Chicago, IL"
            value={formData.current_location}
            onChange={handleChange}
            onBlur={handleBlur}
            className={fieldClass('current_location')}
            disabled={isLoading}
          />
          {touched.current_location && errors.current_location && (
            <span className="input-error-text">{errors.current_location}</span>
          )}
        </div>

        {/* Pickup Location */}
        <div className="input-group" id="field-pickup-location">
          <label htmlFor="pickup_location">Pickup Location</label>
          <input
            type="text"
            id="pickup_location"
            name="pickup_location"
            placeholder="e.g. Kansas City, MO"
            value={formData.pickup_location}
            onChange={handleChange}
            onBlur={handleBlur}
            className={fieldClass('pickup_location')}
            disabled={isLoading}
          />
          {touched.pickup_location && errors.pickup_location && (
            <span className="input-error-text">{errors.pickup_location}</span>
          )}
        </div>

        {/* Dropoff Location */}
        <div className="input-group" id="field-dropoff-location">
          <label htmlFor="dropoff_location">Dropoff Location</label>
          <input
            type="text"
            id="dropoff_location"
            name="dropoff_location"
            placeholder="e.g. Los Angeles, CA"
            value={formData.dropoff_location}
            onChange={handleChange}
            onBlur={handleBlur}
            className={fieldClass('dropoff_location')}
            disabled={isLoading}
          />
          {touched.dropoff_location && errors.dropoff_location && (
            <span className="input-error-text">{errors.dropoff_location}</span>
          )}
        </div>

        {/* Cycle Hours + Start Date row */}
        <div className="trip-form__row">
          <div className="input-group" id="field-cycle-hours">
            <label htmlFor="current_cycle_used">Cycle Hours Used</label>
            <input
              type="number"
              id="current_cycle_used"
              name="current_cycle_used"
              placeholder="0 – 70"
              min="0"
              max="70"
              step="0.5"
              value={formData.current_cycle_used}
              onChange={handleChange}
              onBlur={handleBlur}
              className={fieldClass('current_cycle_used')}
              disabled={isLoading}
            />
            {touched.current_cycle_used && errors.current_cycle_used && (
              <span className="input-error-text">{errors.current_cycle_used}</span>
            )}
          </div>

          <div className="input-group" id="field-start-date">
            <label htmlFor="start_date">Start Date <span className="input-optional">(optional)</span></label>
            <input
              type="date"
              id="start_date"
              name="start_date"
              value={formData.start_date}
              onChange={handleChange}
              disabled={isLoading}
            />
          </div>
        </div>
      </div>

      {/* Submit */}
      <div className="trip-form__actions">
        <button
          type="submit"
          className="btn btn--primary btn--lg"
          id="submit-trip"
          disabled={isLoading}
        >
          {isLoading ? (
            <>
              <span className="btn-spinner"></span>
              Planning Route…
            </>
          ) : (
            'Plan Trip'
          )}
        </button>
      </div>
    </form>
  );
}

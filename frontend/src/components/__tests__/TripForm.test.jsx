import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import TripForm from '../TripForm';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function renderForm(props = {}) {
  const onSubmit = props.onSubmit ?? vi.fn();
  const isLoading = props.isLoading ?? false;
  return {
    onSubmit,
    ...render(<TripForm onSubmit={onSubmit} isLoading={isLoading} />),
  };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TripForm', () => {
  it('renders all required input fields', () => {
    renderForm();

    expect(screen.getByLabelText(/current location/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/pickup location/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/dropoff location/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/cycle hours used/i)).toBeInTheDocument();
  });

  it('renders the submit button', () => {
    renderForm();
    expect(screen.getByRole('button', { name: /plan trip/i })).toBeInTheDocument();
  });

  it('shows validation errors for all required fields when submitted empty', () => {
    renderForm();

    fireEvent.click(screen.getByRole('button', { name: /plan trip/i }));

    expect(screen.getByText(/current location is required/i)).toBeInTheDocument();
    expect(screen.getByText(/pickup location is required/i)).toBeInTheDocument();
    expect(screen.getByText(/dropoff location is required/i)).toBeInTheDocument();
    expect(screen.getByText(/cycle hours are required/i)).toBeInTheDocument();
  });

  it('shows error when cycle hours exceed 70', () => {
    renderForm();

    const cycleInput = screen.getByLabelText(/cycle hours used/i);
    fireEvent.change(cycleInput, { target: { value: '75' } });
    fireEvent.blur(cycleInput);

    expect(screen.getByText(/cannot exceed 70 hours/i)).toBeInTheDocument();
  });

  it('shows error when cycle hours are negative', () => {
    renderForm();

    const cycleInput = screen.getByLabelText(/cycle hours used/i);
    fireEvent.change(cycleInput, { target: { value: '-5' } });
    fireEvent.blur(cycleInput);

    expect(screen.getByText(/cannot be negative/i)).toBeInTheDocument();
  });

  it('calls onSubmit with correct payload when all fields are valid', () => {
    const { onSubmit } = renderForm();

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

    expect(onSubmit).toHaveBeenCalledOnce();
    expect(onSubmit).toHaveBeenCalledWith({
      current_location: 'Chicago, IL',
      pickup_location: 'Kansas City, MO',
      dropoff_location: 'Los Angeles, CA',
      current_cycle_used: 20,
    });
  });

  it('disables inputs and submit button while loading', () => {
    renderForm({ isLoading: true });

    expect(screen.getByLabelText(/current location/i)).toBeDisabled();
    expect(screen.getByLabelText(/pickup location/i)).toBeDisabled();
    expect(screen.getByLabelText(/dropoff location/i)).toBeDisabled();
    expect(screen.getByLabelText(/cycle hours used/i)).toBeDisabled();
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('clears field error when the user starts typing', () => {
    renderForm();

    // Trigger the error first
    fireEvent.click(screen.getByRole('button', { name: /plan trip/i }));
    expect(screen.getByText(/current location is required/i)).toBeInTheDocument();

    // Start typing — error should clear
    fireEvent.change(screen.getByLabelText(/current location/i), {
      target: { value: 'C' },
    });
    expect(screen.queryByText(/current location is required/i)).not.toBeInTheDocument();
  });
});

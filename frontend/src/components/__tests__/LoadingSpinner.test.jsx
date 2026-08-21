import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import LoadingSpinner from '../LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders without throwing', () => {
    expect(() => render(<LoadingSpinner />)).not.toThrow();
  });

  it('renders the default loading message', () => {
    render(<LoadingSpinner />);
    expect(screen.getByText(/Calculating HOS-compliant route/i)).toBeInTheDocument();
  });

  it('renders a custom message when provided', () => {
    render(<LoadingSpinner message="Planning your trip…" />);
    expect(screen.getByText('Planning your trip…')).toBeInTheDocument();
  });

  it('has id="loading-spinner" on the root element', () => {
    render(<LoadingSpinner />);
    expect(document.getElementById('loading-spinner')).toBeInTheDocument();
  });

  it('renders three animated dot spans inside loading-dots', () => {
    const { container } = render(<LoadingSpinner />);
    const dots = container.querySelectorAll('.loading-dots span');
    expect(dots).toHaveLength(3);
  });

  it('renders message in a <p> tag', () => {
    const { container } = render(<LoadingSpinner message="Loading" />);
    expect(container.querySelector('p.loading-message')).toBeInTheDocument();
  });

  it('does not render a <p> tag when no message given', () => {
    // message defaults to non-empty string, so always renders — test falsy override
    const { container } = render(<LoadingSpinner message="" />);
    expect(container.querySelector('p.loading-message')).toBeNull();
  });
});

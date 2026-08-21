import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorBanner from '../ErrorBanner';

describe('ErrorBanner', () => {
  it('returns null when message is empty string', () => {
    const { container } = render(<ErrorBanner message="" onDismiss={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it('returns null when message is null', () => {
    const { container } = render(<ErrorBanner message={null} onDismiss={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it('returns null when message is undefined', () => {
    const { container } = render(<ErrorBanner message={undefined} onDismiss={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders the error message text', () => {
    render(<ErrorBanner message="Something went wrong" onDismiss={vi.fn()} />);
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('has role="alert" for screen reader accessibility', () => {
    render(<ErrorBanner message="API error" onDismiss={vi.fn()} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls onDismiss when dismiss button is clicked', () => {
    const onDismiss = vi.fn();
    render(<ErrorBanner message="Error" onDismiss={onDismiss} />);
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it('has id="error-banner" on the root element', () => {
    render(<ErrorBanner message="Error" onDismiss={vi.fn()} />);
    expect(document.getElementById('error-banner')).toBeInTheDocument();
  });

  it('has id="dismiss-error" on the dismiss button', () => {
    render(<ErrorBanner message="Error" onDismiss={vi.fn()} />);
    expect(document.getElementById('dismiss-error')).toBeInTheDocument();
  });

  it('renders an SVG warning icon', () => {
    const { container } = render(<ErrorBanner message="Error" onDismiss={vi.fn()} />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });
});

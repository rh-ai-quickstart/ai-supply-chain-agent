import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AlertsPanel } from './AlertsPanel';

describe('AlertsPanel', () => {
  it('shows loading alert', () => {
    render(<AlertsPanel loading error="" alerts={[]} />);
    expect(screen.getByText('Loading live state...')).toBeInTheDocument();
  });

  it('shows error alert', () => {
    render(<AlertsPanel loading={false} error="Backend down" alerts={[]} />);
    expect(screen.getByText('Backend down')).toBeInTheDocument();
  });

  it('renders alert rows with correct variants', () => {
    render(
      <AlertsPanel
        loading={false}
        error=""
        alerts={[
          { type: 'critical', text: 'outage' },
          { type: 'warning', text: 'slow' },
        ]}
      />,
    );
    expect(screen.getByText('outage')).toBeInTheDocument();
    expect(screen.getByText('CRITICAL')).toBeInTheDocument();
  });
});

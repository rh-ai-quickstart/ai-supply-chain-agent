import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { DashboardHeader } from './DashboardHeader';

describe('DashboardHeader', () => {
  it('renders title and invokes theme toggle', () => {
    const onToggleTheme = vi.fn();
    render(<DashboardHeader isLightTheme={false} loading={false} onToggleTheme={onToggleTheme} />);
    expect(screen.getByText('Supply Chain Command Center')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Toggle color theme' }));
    expect(onToggleTheme).toHaveBeenCalled();
  });

  it('shows spinner while loading', () => {
    render(<DashboardHeader isLightTheme loading onToggleTheme={() => {}} />);
    expect(screen.getByLabelText('Refreshing data')).toBeInTheDocument();
  });
});

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SystemHealthPanel } from './SystemHealthPanel';

describe('SystemHealthPanel', () => {
  it('renders health metrics for low risk', () => {
    render(
      <SystemHealthPanel
        health={{
          supplierHealth: 92,
          inventoryHealth: 96,
          riskIndex: 20,
          riskLevel: 'low',
          dataFreshnessPercent: 100,
        }}
      />,
    );
    expect(screen.getByText('System Health')).toBeInTheDocument();
    expect(screen.getByText('92%')).toBeInTheDocument();
    expect(screen.getByText('Risk level — Low')).toBeInTheDocument();
  });
});

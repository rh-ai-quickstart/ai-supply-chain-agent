import { Card, CardBody, CardTitle } from '@patternfly/react-core';
import { Line } from 'react-chartjs-2';
import { useTranslation } from 'react-i18next';
import type { ChartData } from 'chart.js';

export interface DemandChartPanelProps {
  data: ChartData<'line'>;
}

export function DemandChartPanel({ data }: DemandChartPanelProps) {
  const { t } = useTranslation('plugin__supply-chain-perspective');

  return (
    <Card className="supply-chain-perspective__dashboard-nested-card" isCompact>
      <CardTitle>{t('Demand Forecast')}</CardTitle>
      <CardBody>
        <div className="supply-chain-perspective__dashboard-chart-box">
          <Line
            data={data}
            options={{
              maintainAspectRatio: false,
              responsive: true,
              plugins: { legend: { position: 'bottom' } },
            }}
          />
        </div>
      </CardBody>
    </Card>
  );
}

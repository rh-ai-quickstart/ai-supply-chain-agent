import { Card, CardBody, CardTitle } from '@patternfly/react-core';
import { Bar } from 'react-chartjs-2';
import { useTranslation } from 'react-i18next';
import type { ChartData } from 'chart.js';

export interface RevenueChartPanelProps {
  data: ChartData<'bar'>;
}

export function RevenueChartPanel({ data }: RevenueChartPanelProps) {
  const { t } = useTranslation('plugin__supply-chain-perspective');

  return (
    <Card className="supply-chain-perspective__dashboard-nested-card" isCompact>
      <CardTitle>{t('Revenue Impact')}</CardTitle>
      <CardBody>
        <div className="supply-chain-perspective__dashboard-chart-box">
          <Bar
            data={data}
            options={{
              maintainAspectRatio: false,
              responsive: true,
              plugins: { legend: { display: false } },
            }}
          />
        </div>
      </CardBody>
    </Card>
  );
}

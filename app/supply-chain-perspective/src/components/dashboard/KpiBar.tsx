import { Card, CardBody, Content } from '@patternfly/react-core';
import { useTranslation } from 'react-i18next';

export interface KpiBarProps {
  kpis: Record<string, { value?: string }>;
}

export function KpiBar({ kpis }: KpiBarProps) {
  const { t } = useTranslation('plugin__supply-chain-perspective');

  const tiles = [
    { label: t('In-Stock Rate'), value: kpis.inStock?.value ?? '--%' },
    { label: t('On-Time Delivery'), value: kpis.onTime?.value ?? '--%' },
    { label: t('Inventory Turnover'), value: kpis.turnover?.value ?? '--x' },
    { label: t('Lost Sales'), value: kpis.lostSales?.value ?? '$--M' },
    { label: t('Optimal Reorder'), value: kpis.reorderPoint?.value ?? '--%' },
  ];

  return (
    <div className="supply-chain-perspective__dashboard-kpi-grid">
      {tiles.map((tile) => (
        <Card key={tile.label} className="supply-chain-perspective__dashboard-kpi-tile" isCompact>
          <CardBody>
            <Content component="small">{tile.label}</Content>
            <Content component="p" className="supply-chain-perspective__dashboard-kpi-metric">
              {tile.value}
            </Content>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}

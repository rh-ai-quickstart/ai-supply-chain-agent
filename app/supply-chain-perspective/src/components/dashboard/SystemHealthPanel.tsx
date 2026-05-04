import { Card, CardBody, CardTitle, Content } from '@patternfly/react-core';
import { useTranslation } from 'react-i18next';
import type { SystemHealthView } from '../../types/dashboard';

export interface SystemHealthPanelProps {
  health: SystemHealthView;
}

interface HealthItemProps {
  label: string;
  value: string;
  fillPercent: number;
  tone: 'good' | 'warn' | 'bad';
}

function HealthItem({ label, value, fillPercent, tone }: HealthItemProps) {
  return (
    <div className="supply-chain-perspective__dashboard-health-item">
      <div className="supply-chain-perspective__dashboard-health-item-header">
        <span className="supply-chain-perspective__dashboard-health-label">{label}</span>
        <span className="supply-chain-perspective__dashboard-health-value">{value}</span>
      </div>
      <div className="supply-chain-perspective__dashboard-health-track">
        <div
          className={`supply-chain-perspective__dashboard-health-fill supply-chain-perspective__dashboard-health-fill--${tone}`}
          style={{ width: `${fillPercent}%` }}
        />
      </div>
    </div>
  );
}

export function SystemHealthPanel({ health }: SystemHealthPanelProps) {
  const { t } = useTranslation('plugin__supply-chain-perspective');

  const riskLabel =
    health.riskLevel === 'critical'
      ? t('Risk level — Critical')
      : health.riskLevel === 'medium'
        ? t('Risk level — Medium')
        : t('Risk level — Low');

  const supplierTone =
    health.supplierHealth >= 90 ? 'good' : health.supplierHealth >= 80 ? 'warn' : 'bad';
  const inventoryTone =
    health.inventoryHealth >= 95 ? 'good' : health.inventoryHealth >= 85 ? 'warn' : 'bad';
  const riskTone = health.riskIndex < 35 ? 'good' : health.riskIndex < 60 ? 'warn' : 'bad';
  const freshnessTone =
    health.dataFreshnessPercent >= 90 ? 'good' : health.dataFreshnessPercent >= 50 ? 'warn' : 'bad';

  return (
    <Card className="supply-chain-perspective__dashboard-nested-card" isCompact>
      <CardTitle>{t('System Health')}</CardTitle>
      <CardBody>
        <Content
          component="small"
          className="supply-chain-perspective__dashboard-muted supply-chain-perspective__dashboard-health-intro"
        >
          {t('Derived from live KPIs and alert severity.')}
        </Content>
        <div className="supply-chain-perspective__dashboard-health-grid">
          <HealthItem
            label={t('Supplier Health')}
            value={`${health.supplierHealth}%`}
            fillPercent={health.supplierHealth}
            tone={supplierTone}
          />
          <HealthItem
            label={t('Inventory Health')}
            value={`${health.inventoryHealth}%`}
            fillPercent={health.inventoryHealth}
            tone={inventoryTone}
          />
          <HealthItem
            label={t('Risk Index')}
            value={riskLabel}
            fillPercent={health.riskIndex}
            tone={riskTone}
          />
          <HealthItem
            label={t('Data Freshness')}
            value={`${health.dataFreshnessPercent}%`}
            fillPercent={health.dataFreshnessPercent}
            tone={freshnessTone}
          />
        </div>
      </CardBody>
    </Card>
  );
}

import { Alert, Card, CardBody, CardTitle, Stack, StackItem } from '@patternfly/react-core';
import { useTranslation } from 'react-i18next';
import type { DashboardAlert } from '../../types/dashboard';

export interface AlertsPanelProps {
  loading: boolean;
  error: string;
  alerts: DashboardAlert[];
}

function alertVariant(type: string | undefined): 'info' | 'warning' | 'danger' | 'success' {
  switch (type) {
    case 'warning':
      return 'warning';
    case 'critical':
      return 'danger';
    case 'info':
      return 'info';
    default:
      return 'info';
  }
}

export function AlertsPanel({ loading, error, alerts }: AlertsPanelProps) {
  const { t } = useTranslation('plugin__supply-chain-perspective');

  return (
    <Card className="supply-chain-perspective__dashboard-nested-card supply-chain-perspective__dashboard-alerts-card">
      <CardTitle>{t('Real-Time Alerts')}</CardTitle>
      <CardBody>
        <div className="supply-chain-perspective__dashboard-alerts-scroll">
          <Stack hasGutter>
            {loading ? (
              <StackItem>
                <Alert variant="info" isInline title={t('Loading live state...')} />
              </StackItem>
            ) : null}
            {error ? (
              <StackItem>
                <Alert variant="danger" isInline title={error} />
              </StackItem>
            ) : null}
            {!loading && !error && !alerts.length ? (
              <StackItem>
                <Alert variant="info" isInline title={t('No active alerts.')} />
              </StackItem>
            ) : null}
            {alerts.slice(0, 8).map((alert, index) => (
              <StackItem key={`${alert.type ?? 'info'}-${index}`}>
                <Alert
                  variant={alertVariant(alert.type)}
                  isInline
                  title={(alert.type ?? 'info').toUpperCase()}
                >
                  {alert.text}
                </Alert>
              </StackItem>
            ))}
          </Stack>
        </div>
      </CardBody>
    </Card>
  );
}

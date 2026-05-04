import {
  Card,
  CardBody,
  CardTitle,
  DescriptionList,
  DescriptionListDescription,
  DescriptionListGroup,
  DescriptionListTerm,
} from '@patternfly/react-core';
import { useTranslation } from 'react-i18next';
import type { SimulationPerformance } from '../../types/dashboard';

export interface PerformanceInsightsProps {
  performance: SimulationPerformance | undefined;
}

export function PerformanceInsights({ performance }: PerformanceInsightsProps) {
  const { t } = useTranslation('plugin__supply-chain-perspective');

  if (!performance) {
    return null;
  }

  const items = [
    { term: t('Inference mode'), desc: performance.mode },
    { term: t('Cache rate'), desc: performance.cacheRate },
    { term: t('Latency'), desc: performance.latency },
    { term: t('Cost savings'), desc: performance.costSavings },
    { term: t('Total tokens'), desc: performance.totalTokens },
    { term: t('Throughput'), desc: performance.tokensPerSecond },
  ].filter((row) => Boolean(row.desc));

  if (!items.length) {
    return null;
  }

  return (
    <Card className="supply-chain-perspective__dashboard-performance-card">
      <CardTitle>{t('Simulation performance')}</CardTitle>
      <CardBody>
        <DescriptionList aria-label={t('Simulation performance')}>
          {items.map((row) => (
            <DescriptionListGroup key={row.term}>
              <DescriptionListTerm>{row.term}</DescriptionListTerm>
              <DescriptionListDescription>{row.desc}</DescriptionListDescription>
            </DescriptionListGroup>
          ))}
        </DescriptionList>
      </CardBody>
    </Card>
  );
}

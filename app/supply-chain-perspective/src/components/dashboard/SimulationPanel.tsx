import { useState } from 'react';
import {
  Button,
  Card,
  CardBody,
  CardTitle,
  Checkbox,
  Form,
  FormGroup,
  Stack,
  StackItem,
  Content,
} from '@patternfly/react-core';
import { useTranslation } from 'react-i18next';
import type { MapViewId } from '../../types/dashboard';

export interface SimulationPanelProps {
  mapView: MapViewId;
  onRunScenario: (_args: { scenario: string; optimize: boolean }) => void;
  onTriggerEvent: (_selectedMapView: MapViewId) => void;
  simulationLoading: boolean;
  simulationError: string;
}

export function SimulationPanel({
  mapView,
  onRunScenario,
  onTriggerEvent,
  simulationLoading,
  simulationError,
}: SimulationPanelProps) {
  const { t } = useTranslation('plugin__supply-chain-perspective');
  const [optimize, setOptimize] = useState(false);

  const handleRun = (scenario: string) => {
    onRunScenario({ scenario, optimize });
  };

  return (
    <Card className="supply-chain-perspective__dashboard-nested-card" isCompact>
      <CardTitle>{t('AI Simulation & Presets')}</CardTitle>
      <CardBody>
        <Form>
          <FormGroup label={t('Infrastructure Engine')} fieldId="optimize-engine">
            <Checkbox
              id="optimize-engine"
              label={t('Enable vLLM & LLM-D')}
              isChecked={optimize}
              onChange={(_event, checked) => setOptimize(checked)}
            />
          </FormGroup>
          <FormGroup label={t('Scenario Presets')} fieldId="scenarios">
            <Stack hasGutter>
              <StackItem>
                <Button
                  variant="secondary"
                  isBlock
                  onClick={() => handleRun('none')}
                  isDisabled={simulationLoading}
                >
                  {t('Live Dashboard')}
                </Button>
              </StackItem>
              <StackItem>
                <Button
                  variant="secondary"
                  isBlock
                  onClick={() => handleRun('port-strike')}
                  isDisabled={simulationLoading}
                >
                  {t('Port Strike LA')}
                </Button>
              </StackItem>
              <StackItem>
                <Button
                  variant="secondary"
                  isBlock
                  onClick={() => handleRun('geopolitical')}
                  isDisabled={simulationLoading}
                >
                  {t('Suez Blockage')}
                </Button>
              </StackItem>
              <StackItem>
                <Button
                  variant="primary"
                  isBlock
                  onClick={() => onTriggerEvent(mapView)}
                  isDisabled={simulationLoading}
                >
                  {t('Trigger World Event')}
                </Button>
              </StackItem>
            </Stack>
          </FormGroup>
        </Form>
        {simulationLoading ? (
          <Content
            component="small"
            className="supply-chain-perspective__dashboard-muted supply-chain-perspective__dashboard-form-footer"
          >
            {t('Running simulation...')}
          </Content>
        ) : null}
        {simulationError ? (
          <Content
            component="small"
            className="supply-chain-perspective__dashboard-error supply-chain-perspective__dashboard-form-footer"
          >
            {simulationError}
          </Content>
        ) : null}
      </CardBody>
    </Card>
  );
}

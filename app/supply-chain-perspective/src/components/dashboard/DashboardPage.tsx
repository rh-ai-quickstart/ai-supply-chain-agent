import { DocumentTitle } from '@openshift-console/dynamic-plugin-sdk';
import { Grid, GridItem, PageSection, Stack, StackItem } from '@patternfly/react-core';
import { useTranslation } from 'react-i18next';
import '../../lib/chartSetup';
import { AlertsPanel } from './AlertsPanel';
import { ChatBar } from './ChatBar';
import { DashboardHeader } from './DashboardHeader';
import { DemandChartPanel } from './DemandChartPanel';
import { KpiBar } from './KpiBar';
import { LogisticsMapPanel } from './LogisticsMapPanel';
import { PerformanceInsights } from './PerformanceInsights';
import { RevenueChartPanel } from './RevenueChartPanel';
import { SimulationPanel } from './SimulationPanel';
import { SystemHealthPanel } from './SystemHealthPanel';
import { useDashboardController } from './useDashboardController';
import './dashboard.css';

export default function DashboardPage() {
  const { t } = useTranslation('plugin__supply-chain-perspective');
  const {
    isLightTheme,
    setIsLightTheme,
    mapView,
    setMapView,
    simulationLoading,
    simulationError,
    chatInput,
    setChatInput,
    chatMessages,
    chatLoading,
    chatError,
    vectorStores,
    vectorStoresLoading,
    vectorStoresError,
    selectedVectorStoreId,
    setSelectedVectorStoreId,
    dashboardState,
    loading,
    error,
    handleRunScenario,
    handleTriggerEvent,
    handleSubmitChat,
    kpis,
    alerts,
    assetCounts,
    selectedMapData,
    demandData,
    revenueData,
    systemHealth,
  } = useDashboardController();

  const rootClass = [
    'supply-chain-perspective__dashboard-root',
    isLightTheme ? 'supply-chain-perspective__dashboard-root--light' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <>
      <DocumentTitle>{t('Supply Chain Command Center')}</DocumentTitle>
      <PageSection hasBodyWrapper={false}>
        <div className={rootClass}>
          <Stack hasGutter>
            <StackItem>
              <DashboardHeader
                isLightTheme={isLightTheme}
                loading={loading}
                onToggleTheme={() => setIsLightTheme((value) => !value)}
              />
            </StackItem>

            <StackItem isFilled>
              <Grid hasGutter className="supply-chain-perspective__dashboard-main-grid">
                <GridItem span={12}>
                  <KpiBar kpis={kpis} />
                </GridItem>

                <GridItem md={3} span={12}>
                  <SimulationPanel
                    mapView={mapView}
                    onRunScenario={handleRunScenario}
                    onTriggerEvent={handleTriggerEvent}
                    simulationLoading={simulationLoading}
                    simulationError={simulationError}
                  />
                </GridItem>

                <GridItem md={6} span={12}>
                  <Stack hasGutter>
                    <StackItem>
                      <Grid hasGutter className="supply-chain-perspective__dashboard-charts-row">
                        <GridItem md={4} span={12}>
                          <DemandChartPanel data={demandData} />
                        </GridItem>
                        <GridItem md={4} span={12}>
                          <RevenueChartPanel data={revenueData} />
                        </GridItem>
                        <GridItem md={4} span={12}>
                          <SystemHealthPanel health={systemHealth} />
                        </GridItem>
                      </Grid>
                    </StackItem>
                    <StackItem>
                      <LogisticsMapPanel
                        mapView={mapView}
                        onChangeMapView={setMapView}
                        selectedMapData={selectedMapData}
                        assetCounts={assetCounts}
                      />
                    </StackItem>
                    <StackItem>
                      <PerformanceInsights performance={dashboardState?.performance} />
                    </StackItem>
                  </Stack>
                </GridItem>

                <GridItem md={3} span={12}>
                  <AlertsPanel loading={loading} error={error} alerts={alerts} />
                </GridItem>
              </Grid>
            </StackItem>

            <StackItem>
              <ChatBar
                chatInput={chatInput}
                onChangeChatInput={setChatInput}
                onSubmitChat={() => void handleSubmitChat()}
                chatLoading={chatLoading}
                chatError={chatError}
                chatMessages={chatMessages}
                vectorStores={vectorStores}
                vectorStoresLoading={vectorStoresLoading}
                vectorStoresError={vectorStoresError}
                selectedVectorStoreId={selectedVectorStoreId}
                onChangeVectorStore={setSelectedVectorStoreId}
              />
            </StackItem>
          </Stack>
        </div>
      </PageSection>
    </>
  );
}

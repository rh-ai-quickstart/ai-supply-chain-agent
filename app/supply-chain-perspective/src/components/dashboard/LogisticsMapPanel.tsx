import 'leaflet/dist/leaflet.css';
import { useMemo } from 'react';
import { Card, CardBody, CardTitle } from '@patternfly/react-core';
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet';
import { useTranslation } from 'react-i18next';
import type { MapLayerData, MapViewId } from '../../types/dashboard';
import { readSemanticToken } from './mapTokens';

export interface LogisticsMapPanelProps {
  mapView: MapViewId;
  onChangeMapView: (_view: MapViewId) => void;
  selectedMapData: MapLayerData;
  assetCounts: { air: number; sea: number; land: number };
}

export function LogisticsMapPanel({
  mapView,
  onChangeMapView,
  selectedMapData,
  assetCounts,
}: LogisticsMapPanelProps) {
  const { t } = useTranslation('plugin__supply-chain-perspective');

  const palette = useMemo(
    () => ({
      portLow: readSemanticToken('--pf-t--global--color--status--success--default', '#3e8635'),
      portHigh: readSemanticToken('--pf-t--global--color--status--danger--default', '#c9190b'),
      air: readSemanticToken('--pf-t--global--palette--blue--400', '#38bdf8'),
      sea: readSemanticToken('--pf-t--global--palette--gold--400', '#fbbf24'),
      land: readSemanticToken('--pf-t--global--palette--purple--400', '#a855f7'),
    }),
    [],
  );

  const assetStroke =
    mapView === 'airFreight' ? palette.air : mapView === 'global' ? palette.sea : palette.land;

  const handleSelectChange = (value: string) => {
    onChangeMapView(value as MapViewId);
  };

  return (
    <Card className="supply-chain-perspective__dashboard-nested-card supply-chain-perspective__dashboard-map-panel">
      <CardTitle>
        <div className="supply-chain-perspective__dashboard-map-header">
          <span>{t('Live Logistics Map')}</span>
          <select
            className="supply-chain-perspective__dashboard-map-select"
            value={mapView}
            onChange={(event) => handleSelectChange(event.target.value)}
            aria-label={t('Map view')}
          >
            <option value="airFreight">{t('Global Air Freight')}</option>
            <option value="global">{t('Global Shipping')}</option>
            <option value="regional">{t('North America')}</option>
          </select>
        </div>
      </CardTitle>
      <CardBody>
        <div className="supply-chain-perspective__dashboard-map-viewport">
          <MapContainer center={[20, 0]} zoom={2} scrollWheelZoom style={{ height: '100%' }}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {(selectedMapData.ports ?? []).map((port) => {
              const isHigh = (port.risk ?? 0) > 15;
              const stroke = isHigh ? palette.portHigh : palette.portLow;
              return (
                <CircleMarker
                  key={`${port.name}-${port.lat}-${port.lng}`}
                  center={[port.lat, port.lng]}
                  radius={7}
                  pathOptions={{
                    color: stroke,
                    fillColor: stroke,
                    fillOpacity: 0.8,
                  }}
                >
                  <Popup>
                    <strong>{port.name}</strong>
                    <br />
                    {t('Risk')}: {port.risk ?? 0}%
                  </Popup>
                </CircleMarker>
              );
            })}
            {(selectedMapData.assets ?? []).map((asset, index) => {
              if (typeof asset.lat !== 'number' || typeof asset.lng !== 'number') {
                return null;
              }
              return (
                <CircleMarker
                  key={asset.id ?? `${asset.name ?? 'asset'}-${index}`}
                  center={[asset.lat, asset.lng]}
                  radius={4}
                  pathOptions={{
                    color: assetStroke,
                    fillColor: assetStroke,
                    fillOpacity: 0.95,
                  }}
                >
                  <Popup>
                    <strong>{asset.name}</strong>
                    <br />
                    {asset.cargo ? `${t('Cargo')}: ${asset.cargo}` : t('Active asset')}
                    {asset.speed ? (
                      <>
                        <br />
                        {t('Speed')}: {asset.speed}
                      </>
                    ) : null}
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>
        </div>
        <div className="supply-chain-perspective__dashboard-muted supply-chain-perspective__dashboard-map-counts">
          {t('Assets summary', {
            air: assetCounts.air,
            sea: assetCounts.sea,
            land: assetCounts.land,
          })}
        </div>
      </CardBody>
    </Card>
  );
}

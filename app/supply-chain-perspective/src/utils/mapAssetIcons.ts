/**
 * Leaflet asset markers aligned with ``app/__legacy/SupplyChainDashboard.html``:
 * plane for live aircraft or air-freight view, truck on regional (non-plane), else vessel.
 */
import * as L from 'leaflet';
import type { MapAsset } from '../types/dashboard';
import type { MapViewId } from '../types/dashboard';

/** Material-style flight icon (same path string as legacy HTML). */
export const PLANE_ICON_PATH =
  'M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z';

const VESSEL_ICON_PATH = 'M12 2 L18 8 V22 H6 V8 L12 2 Z M8 9 H16 V18 H8 Z';

const TRUCK_INNER_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M10 2 H14 V7 H10 Z M11 7 H13 V9 H11 Z M8 9 H16 V23 H8 Z" fill="currentColor"/></svg>`;

export interface AssetIconColors {
  fill: string;
  stroke: string;
}

function assetUsesPlaneIcon(mapView: MapViewId, asset: MapAsset): boolean {
  return asset.is_live === true || mapView === 'airFreight';
}

function assetUsesTruckIcon(mapView: MapViewId, asset: MapAsset): boolean {
  return mapView === 'regional' && !assetUsesPlaneIcon(mapView, asset);
}

export function createAssetDivIcon(
  mapView: MapViewId,
  asset: MapAsset,
  colors: AssetIconColors,
): L.DivIcon {
  const angle = typeof asset.track === 'number' ? asset.track : 0;
  let html: string;

  if (assetUsesTruckIcon(mapView, asset)) {
    html = `<div class="supply-chain-perspective__map-truck-icon" style="transform: rotate(${angle}deg); color:${colors.fill};">${TRUCK_INNER_SVG}</div>`;
  } else {
    const path = assetUsesPlaneIcon(mapView, asset) ? PLANE_ICON_PATH : VESSEL_ICON_PATH;
    html = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" class="supply-chain-perspective__map-asset-svg" style="transform: rotate(${angle}deg); fill:${colors.fill}; stroke:${colors.stroke}; stroke-width:1; overflow:visible;"><path d="${path}"/></svg>`;
  }

  return L.divIcon({
    className: 'supply-chain-perspective__map-asset-marker leaflet-asset-icon',
    html,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
}

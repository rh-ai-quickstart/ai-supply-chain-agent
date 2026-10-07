import PropTypes from "prop-types";
import { useEffect } from "react";
import { useMap } from "react-leaflet";
import {
  diversionRoutePositions,
  featureId,
  featureIdSet,
  featureLatLng,
  resolveMapEntityId,
} from "../../utils/impactEntityUtils";
import { DEFAULT_CENTER, DEFAULT_ZOOM, parseFocusBbox } from "./mapColors";

function fitToPositions(map, positions, { maxZoom, fallbackZoom = 7 } = {}) {
  if (positions.length === 0) {
    map.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
    return;
  }
  if (positions.length === 1) {
    map.setView(positions[0], fallbackZoom);
    return;
  }
  map.fitBounds(positions, { padding: [40, 40], maxZoom });
}

function appendReroutePositions(positions, reroutes) {
  for (const route of reroutes) {
    if (typeof route.latitude === "number" && typeof route.longitude === "number") {
      positions.push([route.latitude, route.longitude]);
    }
  }
}

/**
 * Frame the map on resolved highlighted entity ids (cargo→aircraft already mapped).
 * Accepts a Set or string[] of map feature ids.
 */
export function FitBounds({ features, highlightedIds, reroutes, selectedDiversionKey, focusBbox }) {
  const map = useMap();

  useEffect(() => {
    if (selectedDiversionKey) return;

    const highlighted =
      highlightedIds instanceof Set ? highlightedIds : new Set(highlightedIds || []);
    if (highlighted.size > 0) {
      const focus = features.filter((feature) => highlighted.has(featureId(feature)));
      const positions = focus.map(featureLatLng).filter(Boolean);
      appendReroutePositions(positions, reroutes);
      fitToPositions(map, positions, { maxZoom: 8 });
      return;
    }

    const scenarioCorners = parseFocusBbox(focusBbox);
    if (scenarioCorners) {
      map.fitBounds(scenarioCorners, { padding: [40, 40], maxZoom: 6 });
      return;
    }

    const positions = features.map(featureLatLng).filter(Boolean);
    appendReroutePositions(positions, reroutes);
    fitToPositions(map, positions, { maxZoom: reroutes.length > 0 ? 8 : 6 });
  }, [features, highlightedIds, reroutes, selectedDiversionKey, focusBbox, map]);

  return null;
}

FitBounds.propTypes = {
  features: PropTypes.arrayOf(PropTypes.object),
  highlightedIds: PropTypes.oneOfType([
    PropTypes.instanceOf(Set),
    PropTypes.arrayOf(PropTypes.string),
  ]),
  reroutes: PropTypes.arrayOf(PropTypes.object),
  selectedDiversionKey: PropTypes.string,
  focusBbox: PropTypes.string,
};

export function FocusEntity({ features, focusedEntityId, focusNonce }) {
  const map = useMap();

  useEffect(() => {
    if (!focusedEntityId) return;
    const mapId = resolveMapEntityId(focusedEntityId, featureIdSet(features));
    const feature = features.find((item) => featureId(item) === mapId);
    const coords = featureLatLng(feature);
    if (!coords) return;
    map.setView(coords, Math.max(map.getZoom(), 8), { animate: true });
  }, [focusedEntityId, focusNonce, features, map]);

  return null;
}

FocusEntity.propTypes = {
  features: PropTypes.arrayOf(PropTypes.object),
  focusedEntityId: PropTypes.string,
  focusNonce: PropTypes.number,
};

export function FocusDiversionRoute({ features, route, focusNonce }) {
  const map = useMap();

  useEffect(() => {
    if (!route) return;
    const positions = diversionRoutePositions(route, features);
    if (!positions) {
      if (typeof route.latitude === "number" && typeof route.longitude === "number") {
        map.setView([route.latitude, route.longitude], Math.max(map.getZoom(), 7), {
          animate: true,
        });
      }
      return;
    }
    map.fitBounds(positions, { padding: [60, 60], maxZoom: 8, animate: true });
  }, [route, features, focusNonce, map]);

  return null;
}

FocusDiversionRoute.propTypes = {
  features: PropTypes.arrayOf(PropTypes.object),
  route: PropTypes.object,
  focusNonce: PropTypes.number,
};

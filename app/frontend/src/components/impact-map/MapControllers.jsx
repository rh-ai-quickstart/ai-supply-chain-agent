import PropTypes from "prop-types";
import { useEffect } from "react";
import { useMap } from "react-leaflet";
import { diversionRoutePositions, featureLatLng } from "../../utils/impactEntityUtils";
import { DEFAULT_CENTER, DEFAULT_ZOOM, parseFocusBbox } from "./mapConstants.jsx";

export function FitBounds({ features, highlightedIds, reroutes, selectedDiversionKey, focusBbox }) {
  const map = useMap();

  useEffect(() => {
    if (selectedDiversionKey) return;

    const highlighted = new Set(highlightedIds);
    if (highlighted.size > 0) {
      const focus = features.filter((feature) =>
        highlighted.has(feature.properties?.id ?? feature.id),
      );
      const positions = focus.map(featureLatLng).filter(Boolean);
      for (const route of reroutes) {
        if (typeof route.latitude === "number" && typeof route.longitude === "number") {
          positions.push([route.latitude, route.longitude]);
        }
      }
      if (positions.length === 0) {
        map.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
        return;
      }
      if (positions.length === 1) {
        map.setView(positions[0], 7);
        return;
      }
      map.fitBounds(positions, { padding: [40, 40], maxZoom: 8 });
      return;
    }

    const scenarioCorners = parseFocusBbox(focusBbox);
    if (scenarioCorners) {
      map.fitBounds(scenarioCorners, { padding: [40, 40], maxZoom: 6 });
      return;
    }

    const positions = features.map(featureLatLng).filter(Boolean);
    for (const route of reroutes) {
      if (typeof route.latitude === "number" && typeof route.longitude === "number") {
        positions.push([route.latitude, route.longitude]);
      }
    }

    if (positions.length === 0) {
      map.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
      return;
    }
    if (positions.length === 1) {
      map.setView(positions[0], 7);
      return;
    }
    map.fitBounds(positions, {
      padding: [40, 40],
      maxZoom: reroutes.length > 0 ? 8 : 6,
    });
  }, [features, highlightedIds, reroutes, selectedDiversionKey, focusBbox, map]);

  return null;
}

FitBounds.propTypes = {
  features: PropTypes.arrayOf(PropTypes.object),
  highlightedIds: PropTypes.arrayOf(PropTypes.string),
  reroutes: PropTypes.arrayOf(PropTypes.object),
  selectedDiversionKey: PropTypes.string,
  focusBbox: PropTypes.string,
};

export function FocusEntity({ features, focusedEntityId, focusNonce, resolveMapEntityId }) {
  const map = useMap();

  useEffect(() => {
    if (!focusedEntityId) return;
    const featureIds = new Set(
      features.map((feature) => feature.properties?.id ?? feature.id).filter(Boolean),
    );
    const mapId = resolveMapEntityId(focusedEntityId, featureIds);
    const feature = features.find((item) => (item.properties?.id ?? item.id) === mapId);
    const coords = featureLatLng(feature);
    if (!coords) return;
    map.setView(coords, Math.max(map.getZoom(), 8), { animate: true });
  }, [focusedEntityId, focusNonce, features, map, resolveMapEntityId]);

  return null;
}

FocusEntity.propTypes = {
  features: PropTypes.arrayOf(PropTypes.object),
  focusedEntityId: PropTypes.string,
  focusNonce: PropTypes.number,
  resolveMapEntityId: PropTypes.func.isRequired,
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

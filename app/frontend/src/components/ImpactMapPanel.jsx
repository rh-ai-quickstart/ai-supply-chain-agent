import PropTypes from "prop-types";
import { memo, useMemo } from "react";
import { MapContainer, Polyline, TileLayer } from "react-leaflet";
import {
  diversionKey,
  diversionRoutePositions,
  featureId,
  featureIdSet,
  resolveMapEntityId,
} from "../utils/impactEntityUtils";
import { DiversionMarker, EntityMarker } from "./impact-map/EntityMarkers";
import { FitBounds, FocusDiversionRoute, FocusEntity } from "./impact-map/MapControllers";
import { MapLegend } from "./impact-map/MapLegend";
import {
  DEFAULT_CENTER,
  DEFAULT_ZOOM,
  DIVERSION_SELECTED_COLOR,
} from "./impact-map/mapColors";

export const ImpactMapPanel = memo(function ImpactMapPanel({
  features = [],
  focusBbox = "",
  title = "Impact Map",
  highlightedIds = [],
  reroutes = [],
  focusedEntityId = "",
  focusNonce = 0,
  selectedDiversionKey = "",
  diversionFocusNonce = 0,
  valueByEntity = new Map(),
  supplyChainIndexes = null,
  currency = "USD",
  loading = false,
  error = "",
  warning = "",
}) {
  const ids = useMemo(() => featureIdSet(features), [features]);
  const highlighted = useMemo(() => {
    const resolved = new Set();
    for (const rawId of highlightedIds) {
      const mapped = resolveMapEntityId(rawId, ids);
      if (mapped) resolved.add(mapped);
      if (rawId) resolved.add(rawId);
    }
    return resolved;
  }, [highlightedIds, ids]);

  const focusedMapId = resolveMapEntityId(focusedEntityId, ids);
  const selectedRoute = useMemo(
    () => reroutes.find((route) => diversionKey(route) === selectedDiversionKey) || null,
    [reroutes, selectedDiversionKey],
  );
  const selectedRoutePositions = useMemo(
    () => (selectedRoute ? diversionRoutePositions(selectedRoute, features) : null),
    [selectedRoute, features],
  );

  return (
    <article className="panel map-panel impact-map-panel">
      <div className="map-header">
        <h3>{title}</h3>
        {loading ? (
          <span className="muted">Loading entities…</span>
        ) : (
          <span className="muted">Entities: {features.length}</span>
        )}
      </div>
      {error ? <p className="error">{error}</p> : null}
      {warning ? <p className="muted" role="status">{warning}</p> : null}
      {!loading && !error && features.length === 0 ? (
        <p className="muted">No map entities yet.</p>
      ) : null}
      <div className="map-viewport">
        <MapContainer
          center={DEFAULT_CENTER}
          zoom={DEFAULT_ZOOM}
          scrollWheelZoom
          style={{ height: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitBounds
            features={features}
            focusBbox={focusBbox}
            highlightedIds={highlighted}
            reroutes={reroutes}
            selectedDiversionKey={selectedDiversionKey}
          />
          {!selectedDiversionKey ? (
            <FocusEntity
              features={features}
              focusedEntityId={focusedEntityId}
              focusNonce={focusNonce}
            />
          ) : null}
          <FocusDiversionRoute
            features={features}
            route={selectedRoute}
            focusNonce={diversionFocusNonce}
          />
          {features.map((feature) => {
            const id = featureId(feature);
            return (
              <EntityMarker
                key={id}
                feature={feature}
                isHighlighted={highlighted.has(id)}
                isFocused={Boolean(focusedMapId) && focusedMapId === id}
                focusNonce={focusNonce}
                valueByEntity={valueByEntity}
                affectedIds={highlightedIds}
                currency={currency}
                supplyChainIndexes={supplyChainIndexes}
              />
            );
          })}
          {selectedRoutePositions ? (
            <Polyline
              positions={selectedRoutePositions}
              pathOptions={{
                color: DIVERSION_SELECTED_COLOR,
                weight: 3,
                opacity: 0.95,
                dashArray: "10 8",
              }}
            />
          ) : null}
          {reroutes.map((route) => (
            <DiversionMarker
              key={`reroute-${diversionKey(route)}`}
              route={route}
              isSelected={selectedDiversionKey === diversionKey(route)}
              focusNonce={diversionFocusNonce}
            />
          ))}
        </MapContainer>
        <MapLegend />
      </div>
      <div className="muted map-counts">
        Entities: {features.length} | Highlighted: {highlightedIds.length} | Diversions:{" "}
        {reroutes.length}
      </div>
    </article>
  );
});

ImpactMapPanel.propTypes = {
  features: PropTypes.arrayOf(PropTypes.object),
  focusBbox: PropTypes.string,
  title: PropTypes.string,
  highlightedIds: PropTypes.arrayOf(PropTypes.string),
  reroutes: PropTypes.arrayOf(
    PropTypes.shape({
      entity_id: PropTypes.string,
      target_id: PropTypes.string,
      target_label: PropTypes.string,
      latitude: PropTypes.number,
      longitude: PropTypes.number,
      rationale: PropTypes.string,
    }),
  ),
  focusedEntityId: PropTypes.string,
  focusNonce: PropTypes.number,
  selectedDiversionKey: PropTypes.string,
  diversionFocusNonce: PropTypes.number,
  valueByEntity: PropTypes.instanceOf(Map),
  supplyChainIndexes: PropTypes.shape({
    cargoByCarrier: PropTypes.instanceOf(Map),
    skusByCarrier: PropTypes.instanceOf(Map),
  }),
  currency: PropTypes.string,
  loading: PropTypes.bool,
  error: PropTypes.string,
  warning: PropTypes.string,
};

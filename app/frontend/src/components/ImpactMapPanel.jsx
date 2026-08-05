import PropTypes from "prop-types";
import { memo, useEffect, useMemo, useRef } from "react";
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import {
  aircraftValueUsd,
  cargoCostForAircraft,
  diversionKey,
  diversionRoutePositions,
  featureLatLng,
  flightInfoFromFeature,
  formatCurrency,
  resolveMapEntityId,
} from "../utils/impactEntityUtils";

const DEFAULT_CENTER = [51.5, -0.5];
const DEFAULT_ZOOM = 5;
const DIVERSION_COLOR = "#2ECC71";
const DIVERSION_SELECTED_COLOR = "#F1C40F";

function FitBounds({ features, highlightedIds, reroutes, selectedDiversionKey }) {
  const map = useMap();

  useEffect(() => {
    if (selectedDiversionKey) return;

    const highlighted = new Set(highlightedIds);
    const focus =
      highlighted.size > 0
        ? features.filter((feature) => highlighted.has(feature.properties?.id ?? feature.id))
        : features;

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
    map.fitBounds(positions, {
      padding: [40, 40],
      maxZoom: highlighted.size > 0 || reroutes.length > 0 ? 8 : 6,
    });
  }, [features, highlightedIds, reroutes, selectedDiversionKey, map]);

  return null;
}

function FocusEntity({ features, focusedEntityId, focusNonce }) {
  const map = useMap();
  const featureIds = useMemo(
    () => new Set(features.map((feature) => feature.properties?.id ?? feature.id).filter(Boolean)),
    [features],
  );

  useEffect(() => {
    if (!focusedEntityId) return;
    const mapId = resolveMapEntityId(focusedEntityId, featureIds);
    const feature = features.find((item) => (item.properties?.id ?? item.id) === mapId);
    const coords = featureLatLng(feature);
    if (!coords) return;
    map.setView(coords, Math.max(map.getZoom(), 8), { animate: true });
  }, [focusedEntityId, focusNonce, features, featureIds, map]);

  return null;
}

function FocusDiversionRoute({ features, route, focusNonce }) {
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

function EntityMarker({
  feature,
  isHighlighted,
  isFocused,
  focusNonce,
  focusedEntityId,
  valueByEntity,
  affectedIds,
  currency,
}) {
  const markerRef = useRef(null);
  const info = flightInfoFromFeature(feature);
  const flightValue = aircraftValueUsd(info.id, valueByEntity, info);
  const cargoOnBoard = cargoCostForAircraft(info.id, valueByEntity, affectedIds);
  const focusedCargoValue =
    focusedEntityId?.startsWith("cargo-") &&
    (focusedEntityId === `cargo-${info.id}` ||
      focusedEntityId.startsWith(`cargo-${info.id}-`))
      ? valueByEntity.get(focusedEntityId)
      : null;
  const totalAtRisk =
    (Number.isFinite(flightValue) ? flightValue : 0) +
    (Number.isFinite(cargoOnBoard) ? cargoOnBoard : 0);
  const showTotal =
    Number.isFinite(flightValue) && Number.isFinite(cargoOnBoard) && totalAtRisk > 0;

  useEffect(() => {
    if (!isFocused || !markerRef.current) return;
    markerRef.current.openPopup();
  }, [isFocused, focusNonce]);

  const coords = featureLatLng(feature);
  if (!coords) return null;

  return (
    <CircleMarker
      ref={markerRef}
      center={coords}
      radius={isHighlighted || isFocused ? 9 : 5}
      pathOptions={{
        color: isFocused ? "#FFC312" : isHighlighted ? "#FF4757" : "#00E0FF",
        fillColor: isFocused ? "#FFC312" : isHighlighted ? "#FF4757" : "#00E0FF",
        fillOpacity: isHighlighted || isFocused ? 0.9 : 0.55,
        weight: isHighlighted || isFocused ? 2 : 1,
      }}
    >
      <Popup>
        <div className="impact-map-popup">
          <strong>{info.callSign || info.id}</strong>
          {info.callSign && info.id !== info.callSign ? (
            <>
              <br />
              <span className="muted">ID: {info.id}</span>
            </>
          ) : null}
          {info.type ? (
            <>
              <br />
              Type: {info.type}
            </>
          ) : null}
          {info.status ? (
            <>
              <br />
              Status: {info.status}
            </>
          ) : null}
          {info.route ? (
            <>
              <br />
              Route: {info.route}
            </>
          ) : null}
          {info.originCountry ? (
            <>
              <br />
              Origin: {info.originCountry}
            </>
          ) : null}
          {Number.isFinite(flightValue) ? (
            <>
              <br />
              Flight value: {formatCurrency(flightValue, currency)}
            </>
          ) : null}
          {Number.isFinite(cargoOnBoard) ? (
            <>
              <br />
              Cargo on board: {formatCurrency(cargoOnBoard, currency)}
            </>
          ) : null}
          {Number.isFinite(focusedCargoValue) ? (
            <>
              <br />
              Selected cargo ({focusedEntityId}): {formatCurrency(focusedCargoValue, currency)}
            </>
          ) : null}
          {showTotal ? (
            <>
              <br />
              <strong>Total at risk: {formatCurrency(totalAtRisk, currency)}</strong>
            </>
          ) : null}
          {isHighlighted ? (
            <>
              <br />
              Affected by scenario
            </>
          ) : null}
        </div>
      </Popup>
    </CircleMarker>
  );
}

EntityMarker.propTypes = {
  feature: PropTypes.object.isRequired,
  isHighlighted: PropTypes.bool,
  isFocused: PropTypes.bool,
  focusNonce: PropTypes.number,
  focusedEntityId: PropTypes.string,
  valueByEntity: PropTypes.instanceOf(Map),
  affectedIds: PropTypes.arrayOf(PropTypes.string),
  currency: PropTypes.string,
};

function DiversionMarker({ route, isSelected, focusNonce }) {
  const markerRef = useRef(null);

  useEffect(() => {
    if (!isSelected || !markerRef.current) return;
    markerRef.current.openPopup();
  }, [isSelected, focusNonce]);

  if (typeof route.latitude !== "number" || typeof route.longitude !== "number") {
    return null;
  }

  return (
    <CircleMarker
      ref={markerRef}
      center={[route.latitude, route.longitude]}
      radius={isSelected ? 12 : 10}
      pathOptions={{
        color: isSelected ? DIVERSION_SELECTED_COLOR : DIVERSION_COLOR,
        fillColor: isSelected ? DIVERSION_SELECTED_COLOR : DIVERSION_COLOR,
        fillOpacity: 0.85,
        weight: isSelected ? 3 : 2,
      }}
    >
      <Popup>
        <strong>{route.target_label || route.target_id}</strong>
        {route.entity_id ? (
          <>
            <br />
            Divert: {route.entity_id}
          </>
        ) : null}
        {route.rationale ? (
          <>
            <br />
            {route.rationale}
          </>
        ) : null}
      </Popup>
    </CircleMarker>
  );
}

DiversionMarker.propTypes = {
  route: PropTypes.shape({
    entity_id: PropTypes.string,
    target_id: PropTypes.string,
    target_label: PropTypes.string,
    latitude: PropTypes.number,
    longitude: PropTypes.number,
    rationale: PropTypes.string,
  }).isRequired,
  isSelected: PropTypes.bool,
  focusNonce: PropTypes.number,
};

export const ImpactMapPanel = memo(function ImpactMapPanel({
  features = [],
  highlightedIds = [],
  reroutes = [],
  focusedEntityId = "",
  focusNonce = 0,
  selectedDiversionKey = "",
  diversionFocusNonce = 0,
  valueByEntity = new Map(),
  currency = "USD",
  loading = false,
  error = "",
  warning = "",
}) {
  const featureIds = useMemo(
    () => new Set(features.map((feature) => feature.properties?.id ?? feature.id).filter(Boolean)),
    [features],
  );
  const highlighted = useMemo(() => {
    const ids = new Set();
    for (const rawId of highlightedIds) {
      const mapped = resolveMapEntityId(rawId, featureIds);
      if (mapped) ids.add(mapped);
      if (rawId) ids.add(rawId);
    }
    return ids;
  }, [highlightedIds, featureIds]);

  const focusedMapId = resolveMapEntityId(focusedEntityId, featureIds);
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
        <h3>Impact Map</h3>
        {loading ? <span className="muted">Loading entities…</span> : null}
      </div>
      {error ? <p className="error">{error}</p> : null}
      {warning ? <p className="muted" role="status">{warning}</p> : null}
      {!loading && !error && features.length === 0 ? (
        <p className="muted">No map entities for this scenario yet.</p>
      ) : null}
      <div className="map-viewport">
        <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} scrollWheelZoom style={{ height: "100%" }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitBounds
            features={features}
            highlightedIds={highlightedIds}
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
            const id = feature.properties?.id ?? feature.id;
            return (
              <EntityMarker
                key={id}
                feature={feature}
                isHighlighted={highlighted.has(id)}
                isFocused={Boolean(focusedMapId) && focusedMapId === id}
                focusNonce={focusNonce}
                focusedEntityId={focusedEntityId}
                valueByEntity={valueByEntity}
                affectedIds={highlightedIds}
                currency={currency}
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
  currency: PropTypes.string,
  loading: PropTypes.bool,
  error: PropTypes.string,
  warning: PropTypes.string,
};

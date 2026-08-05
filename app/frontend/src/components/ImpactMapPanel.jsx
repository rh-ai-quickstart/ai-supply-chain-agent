import PropTypes from "prop-types";
import { memo, useEffect } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";

const DEFAULT_CENTER = [51.5, -0.5];
const DEFAULT_ZOOM = 5;

function pointCoords(feature) {
  const geometry = feature?.geometry;
  if (!geometry || geometry.type !== "Point" || !Array.isArray(geometry.coordinates)) {
    return null;
  }
  const [lon, lat] = geometry.coordinates;
  if (typeof lon !== "number" || typeof lat !== "number") {
    return null;
  }
  return [lat, lon];
}

function FitBounds({ features, highlightedIds, reroutes }) {
  const map = useMap();

  useEffect(() => {
    const highlighted = new Set(highlightedIds);
    const focus =
      highlighted.size > 0
        ? features.filter((feature) => highlighted.has(feature.properties?.id ?? feature.id))
        : features;

    const positions = focus.map(pointCoords).filter(Boolean);
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
  }, [features, highlightedIds, reroutes, map]);

  return null;
}

export const ImpactMapPanel = memo(function ImpactMapPanel({
  features = [],
  highlightedIds = [],
  reroutes = [],
  loading = false,
  error = "",
}) {
  const highlighted = new Set(highlightedIds);

  return (
    <article className="panel map-panel impact-map-panel">
      <div className="map-header">
        <h3>Impact Map</h3>
        {loading ? <span className="muted">Loading entities…</span> : null}
      </div>
      {error ? <p className="error">{error}</p> : null}
      <div className="map-viewport">
        <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} scrollWheelZoom style={{ height: "100%" }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitBounds features={features} highlightedIds={highlightedIds} reroutes={reroutes} />
          {features.map((feature) => {
            const coords = pointCoords(feature);
            if (!coords) return null;
            const id = feature.properties?.id ?? feature.id;
            const isHighlighted = highlighted.has(id);
            const status = feature.properties?.status;
            const entityType = feature.properties?.type;
            return (
              <CircleMarker
                key={id}
                center={coords}
                radius={isHighlighted ? 9 : 5}
                pathOptions={{
                  color: isHighlighted ? "#FF4757" : "#00E0FF",
                  fillColor: isHighlighted ? "#FF4757" : "#00E0FF",
                  fillOpacity: isHighlighted ? 0.9 : 0.55,
                  weight: isHighlighted ? 2 : 1,
                }}
              >
                <Popup>
                  <strong>{id}</strong>
                  {entityType ? (
                    <>
                      <br />
                      Type: {entityType}
                    </>
                  ) : null}
                  {status ? (
                    <>
                      <br />
                      Status: {status}
                    </>
                  ) : null}
                  {isHighlighted ? (
                    <>
                      <br />
                      Affected by scenario
                    </>
                  ) : null}
                </Popup>
              </CircleMarker>
            );
          })}
          {reroutes.map((route) => {
            if (typeof route.latitude !== "number" || typeof route.longitude !== "number") {
              return null;
            }
            return (
              <CircleMarker
                key={`reroute-${route.entity_id}-${route.target_id}`}
                center={[route.latitude, route.longitude]}
                radius={10}
                pathOptions={{
                  color: "#2ECC71",
                  fillColor: "#2ECC71",
                  fillOpacity: 0.85,
                  weight: 2,
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
          })}
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
  loading: PropTypes.bool,
  error: PropTypes.string,
};

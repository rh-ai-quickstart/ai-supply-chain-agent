import PropTypes from "prop-types";
import { useEffect, useRef } from "react";
import { CircleMarker, Marker, Popup } from "react-leaflet";
import { FlightEntityPopup } from "../FlightEntityPopup.jsx";
import { featureLatLng, flightInfoFromFeature } from "../../utils/impactEntityUtils";
import {
  DIVERSION_COLOR,
  DIVERSION_SELECTED_COLOR,
  KIND_COLORS,
  MAP_COLORS,
  entityIcon,
  kindForType,
} from "./mapConstants.jsx";

export function EntityMarker({
  feature,
  isHighlighted,
  isFocused,
  focusNonce,
  valueByEntity,
  affectedIds,
  currency,
  supplyChainIndexes,
}) {
  const markerRef = useRef(null);
  const info = flightInfoFromFeature(feature);

  useEffect(() => {
    if (!isFocused || !markerRef.current) return;
    markerRef.current.openPopup();
  }, [isFocused, focusNonce]);

  const coords = featureLatLng(feature);
  if (!coords) return null;

  const kind = kindForType(info.type);
  const markerColor = isFocused
    ? MAP_COLORS.focused
    : isHighlighted
      ? MAP_COLORS.affected
      : KIND_COLORS[kind] || MAP_COLORS.flight;
  const isFlight = kind === "flight";

  return (
    <Marker
      ref={markerRef}
      position={coords}
      icon={entityIcon(kind, markerColor, isHighlighted || isFocused)}
    >
      <Popup className="flight-popup-leaflet" maxWidth={360} minWidth={280}>
        {isFlight ? (
          <FlightEntityPopup
            info={info}
            valueByEntity={valueByEntity}
            affectedIds={affectedIds}
            currency={currency}
            supplyChainIndexes={supplyChainIndexes}
            isHighlighted={isHighlighted}
          />
        ) : (
          <div className="impact-map-popup">
            <strong>{info.callSign || info.id}</strong>
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
            {isHighlighted ? (
              <>
                <br />
                Affected by scenario
              </>
            ) : null}
          </div>
        )}
      </Popup>
    </Marker>
  );
}

EntityMarker.propTypes = {
  feature: PropTypes.object.isRequired,
  supplyChainIndexes: PropTypes.shape({
    cargoByCarrier: PropTypes.instanceOf(Map),
    skusByCarrier: PropTypes.instanceOf(Map),
  }),
  isHighlighted: PropTypes.bool,
  isFocused: PropTypes.bool,
  focusNonce: PropTypes.number,
  valueByEntity: PropTypes.instanceOf(Map),
  affectedIds: PropTypes.arrayOf(PropTypes.string),
  currency: PropTypes.string,
};

export function DiversionMarker({ route, isSelected, focusNonce }) {
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

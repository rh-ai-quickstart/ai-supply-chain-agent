import L from "leaflet";
import { renderToStaticMarkup } from "react-dom/server";
import { Building2, PlaneTakeoff, Anchor } from "lucide-react";

const ENTITY_ICONS = {
  flight: PlaneTakeoff,
  facility: Building2,
  vessel: Anchor,
};

/** Render a lucide icon to an inline SVG string for use in a Leaflet divIcon. */
export function entityIconHtml(kind, color, size, strokeWidth) {
  const Icon = ENTITY_ICONS[kind] || ENTITY_ICONS.facility;
  return renderToStaticMarkup(
    <span className="impact-entity-glyph" style={{ color }}>
      <Icon size={size} strokeWidth={strokeWidth} aria-hidden="true" />
    </span>,
  );
}

/** ``L.divIcon`` for an entity kind, tinted by the current marker state color. */
export function entityIcon(kind, color, isEmphasized) {
  const size = isEmphasized ? 34 : 26;
  const strokeWidth = isEmphasized ? 2 : 1.75;
  return L.divIcon({
    className: "impact-entity-icon",
    html: entityIconHtml(kind, color, size, strokeWidth),
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

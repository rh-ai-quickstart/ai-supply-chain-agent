import PropTypes from "prop-types";
import { entityIconHtml, KIND_COLORS, MAP_COLORS, MAP_LEGEND_ITEMS } from "./mapConstants.jsx";

export function MapLegend() {
  return (
    <ul className="impact-map-legend" aria-label="Map legend">
      {MAP_LEGEND_ITEMS.map((item) => (
        <li key={item.label} className="impact-map-legend-item">
          {item.kind ? (
            <span
              className="impact-map-legend-icon"
              dangerouslySetInnerHTML={{
                __html: entityIconHtml(
                  item.kind,
                  KIND_COLORS[item.kind] || MAP_COLORS.flight,
                  14,
                  2,
                ),
              }}
            />
          ) : (
            <span
              className="impact-map-legend-swatch"
              style={{ backgroundColor: item.color }}
              aria-hidden="true"
            />
          )}
          <span>{item.label}</span>
        </li>
      ))}
    </ul>
  );
}

MapLegend.propTypes = {};

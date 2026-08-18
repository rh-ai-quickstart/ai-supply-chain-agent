import PropTypes from "prop-types";
import { InfoTooltip } from "./InfoTooltip";

export function SectionHeading({ id, children, tooltip, className = "" }) {
  const rootClassName = ["section-heading", className].filter(Boolean).join(" ");

  return (
    <div className={rootClassName}>
      <h3 id={id}>{children}</h3>
      {tooltip ? (
        <InfoTooltip label={`About ${children}`} content={tooltip} />
      ) : null}
    </div>
  );
}

SectionHeading.propTypes = {
  id: PropTypes.string,
  children: PropTypes.node.isRequired,
  tooltip: PropTypes.string,
  className: PropTypes.string,
};

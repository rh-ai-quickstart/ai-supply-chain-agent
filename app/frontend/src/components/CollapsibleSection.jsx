import PropTypes from "prop-types";
import { useId, useState } from "react";
import { ChevronDown } from "lucide-react";
import { InfoTooltip } from "./InfoTooltip";

export function CollapsibleSection({
  title,
  tooltip = "",
  tooltipLabel = "",
  defaultOpen = false,
  className = "",
  children,
}) {
  const [open, setOpen] = useState(defaultOpen);
  const contentId = useId();
  const rootClassName = ["collapsible-section", open ? "is-open" : "is-collapsed", className]
    .filter(Boolean)
    .join(" ");
  const hintLabel = tooltipLabel || (typeof title === "string" ? `About ${title}` : "About this section");

  return (
    <div className={rootClassName}>
      <div className="collapsible-section__header">
        <button
          type="button"
          className="collapsible-section__trigger"
          aria-expanded={open}
          aria-controls={contentId}
          onClick={() => setOpen((value) => !value)}
        >
          <span className="collapsible-section__title">{title}</span>
          <ChevronDown size={16} className="collapsible-section__chevron" aria-hidden="true" />
        </button>
        {tooltip ? (
          <InfoTooltip
            label={hintLabel}
            content={tooltip}
            className="collapsible-section__hint"
          />
        ) : null}
      </div>
      {open ? (
        <div id={contentId} className="collapsible-section__content">
          {children}
        </div>
      ) : null}
    </div>
  );
}

CollapsibleSection.propTypes = {
  title: PropTypes.node.isRequired,
  tooltip: PropTypes.string,
  tooltipLabel: PropTypes.string,
  defaultOpen: PropTypes.bool,
  className: PropTypes.string,
  children: PropTypes.node,
};

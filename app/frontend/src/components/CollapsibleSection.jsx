import PropTypes from "prop-types";
import { useId, useState } from "react";
import { ChevronDown } from "lucide-react";

export function CollapsibleSection({
  title,
  defaultOpen = false,
  className = "",
  children,
}) {
  const [open, setOpen] = useState(defaultOpen);
  const contentId = useId();
  const rootClassName = ["collapsible-section", open ? "is-open" : "is-collapsed", className]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={rootClassName}>
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
  defaultOpen: PropTypes.bool,
  className: PropTypes.string,
  children: PropTypes.node,
};

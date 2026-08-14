import PropTypes from "prop-types";
import { useCallback, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { CircleHelp } from "lucide-react";

const TOOLTIP_MARGIN = 8;
const VIEWPORT_PADDING = 8;

function computeTooltipPosition(trigger, placement = "auto") {
  const rect = trigger.getBoundingClientRect();
  const spaceAbove = rect.top;
  const spaceBelow = window.innerHeight - rect.bottom;
  const placeAbove =
    placement === "top"
      ? true
      : placement === "bottom"
        ? false
        : spaceAbove >= spaceBelow;

  const anchorY = placeAbove ? rect.top - TOOLTIP_MARGIN : rect.bottom + TOOLTIP_MARGIN;
  const centerX = rect.left + rect.width / 2;
  const clampedX = Math.min(
    window.innerWidth - VIEWPORT_PADDING,
    Math.max(VIEWPORT_PADDING, centerX),
  );

  return { x: clampedX, y: anchorY, placeAbove };
}

/**
 * Small help icon that reveals explanatory text on hover or keyboard focus.
 * Tooltip content is portaled to escape overflow clipping in scroll panels.
 */
export function InfoTooltip({ label, content, className = "", placement = "auto" }) {
  const tooltipId = useId();
  const triggerRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0, placeAbove: true });
  const text = (content || "").trim();

  const updatePosition = useCallback(() => {
    if (!triggerRef.current) {
      return;
    }
    setPosition(computeTooltipPosition(triggerRef.current, placement));
  }, [placement]);

  const show = useCallback(() => {
    updatePosition();
    setOpen(true);
  }, [updatePosition]);

  const hide = useCallback(() => {
    setOpen(false);
  }, []);

  useLayoutEffect(() => {
    if (!open) {
      return undefined;
    }
    updatePosition();
    const onScrollOrResize = () => updatePosition();
    window.addEventListener("scroll", onScrollOrResize, true);
    window.addEventListener("resize", onScrollOrResize);
    return () => {
      window.removeEventListener("scroll", onScrollOrResize, true);
      window.removeEventListener("resize", onScrollOrResize);
    };
  }, [open, updatePosition]);

  if (!text) {
    return null;
  }

  const rootClassName = ["info-tooltip", className].filter(Boolean).join(" ");
  const bubbleClassName = [
    "info-tooltip__content",
    "info-tooltip__content--portal",
    position.placeAbove ? "info-tooltip__content--above" : "info-tooltip__content--below",
  ].join(" ");

  return (
    <>
      <span className={rootClassName}>
        <button
          ref={triggerRef}
          type="button"
          className="info-tooltip__trigger"
          aria-label={label}
          aria-describedby={open ? tooltipId : undefined}
          onMouseEnter={show}
          onMouseLeave={hide}
          onFocus={show}
          onBlur={hide}
        >
          <CircleHelp size={14} aria-hidden="true" />
        </button>
      </span>
      {open
        ? createPortal(
            <span
              id={tooltipId}
              role="tooltip"
              className={bubbleClassName}
              style={{
                left: `${position.x}px`,
                top: `${position.y}px`,
              }}
            >
              {text}
            </span>,
            document.body,
          )
        : null}
    </>
  );
}

InfoTooltip.propTypes = {
  label: PropTypes.string.isRequired,
  content: PropTypes.string.isRequired,
  className: PropTypes.string,
  placement: PropTypes.oneOf(["auto", "top", "bottom"]),
};

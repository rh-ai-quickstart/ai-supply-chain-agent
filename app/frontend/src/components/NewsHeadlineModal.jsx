import PropTypes from "prop-types";
import { useEffect, useRef } from "react";

function headlineTitle(item) {
  return item?.title?.trim() || "News headline";
}

export function NewsHeadlineModal({ item, onClose, onCreateScenario }) {
  const previouslyFocusedRef = useRef(null);
  const hasLink = Boolean(item?.link?.trim());
  const title = headlineTitle(item);

  useEffect(() => {
    previouslyFocusedRef.current = document.activeElement;

    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose?.();
      }
    };
    window.addEventListener("keydown", onKeyDown);

    return () => {
      window.removeEventListener("keydown", onKeyDown);
      const prior = previouslyFocusedRef.current;
      if (prior && typeof prior.focus === "function") {
        prior.focus();
      }
    };
  }, [onClose]);

  const handleReadArticle = () => {
    if (!hasLink) return;
    window.open(item.link, "_blank", "noopener,noreferrer");
    onClose?.();
  };

  const handleCreateScenario = () => {
    onCreateScenario?.(item);
    onClose?.();
  };

  return (
    <div
      className="chat-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="news-headline-modal-title"
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose?.();
        }
      }}
    >
      <div className="chat-modal-content news-headline-modal">
        <div className="chat-modal-header">
          <h3 id="news-headline-modal-title">{title}</h3>
          <button type="button" className="chat-modal-dismiss" onClick={onClose} aria-label="Close dialog">
            ×
          </button>
        </div>
        <div className="news-headline-modal-body">
          {item?.source ? (
            <p className="news-headline-modal-meta muted">
              <strong>Source:</strong> {item.source}
            </p>
          ) : null}
          {item?.published_at ? (
            <p className="news-headline-modal-meta muted">
              <strong>Published:</strong> {item.published_at}
            </p>
          ) : null}
          {item?.summary?.trim() ? (
            <p className="news-headline-modal-summary">{item.summary.trim()}</p>
          ) : (
            <p className="muted">No summary available for this headline.</p>
          )}
          <div className="news-headline-modal-actions">
            <button
              type="button"
              className="btn news-headline-modal-btn"
              onClick={handleReadArticle}
              disabled={!hasLink}
            >
              Read article
            </button>
            <button type="button" className="kb-submit news-headline-modal-btn" onClick={handleCreateScenario}>
              Create scenario
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

NewsHeadlineModal.propTypes = {
  item: PropTypes.shape({
    title: PropTypes.string,
    link: PropTypes.string,
    source: PropTypes.string,
    published_at: PropTypes.string,
    summary: PropTypes.string,
  }).isRequired,
  onClose: PropTypes.func,
  onCreateScenario: PropTypes.func,
};

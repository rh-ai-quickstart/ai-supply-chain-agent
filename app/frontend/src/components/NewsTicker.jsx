import PropTypes from "prop-types";
import { useState } from "react";
import { Globe2 } from "lucide-react";
import { InfoTooltip } from "./InfoTooltip";
import { NewsHeadlineModal } from "./NewsHeadlineModal";

function NewsLabel() {
  return (
    <span className="news-ticker-label">
      News
      <InfoTooltip
        label="About supply chain news"
        content="Headlines from RSS feeds. Click a headline to read the article or create a scenario from that story."
        className="news-ticker-label__hint"
      />
    </span>
  );
}

const SEPARATOR = "  ·  ";

function headlineLabel(item) {
  return item.source ? `${item.source}: ${item.title}` : item.title;
}

export function NewsTicker({ items = [], loading = false, onCreateScenarioFromNews, embedded = false }) {
  const [selectedHeadline, setSelectedHeadline] = useState(null);
  const headlines = Array.isArray(items) ? items.filter((item) => item?.title) : [];
  const tickerClassName = embedded ? "news-ticker news-ticker--embedded" : "news-ticker";

  if (!loading && headlines.length === 0) {
    return (
      <div className={tickerClassName} role="status" aria-live="polite">
        <NewsLabel />
        <div className="news-ticker-viewport">
          <span className="news-ticker-empty muted">No headlines available</span>
        </div>
      </div>
    );
  }

  const sequence = headlines.length
    ? headlines
    : [{ title: "Loading latest headlines…", link: "", source: "" }];

  // Duplicate the sequence so the CSS marquee can loop seamlessly.
  const loop = [...sequence, ...sequence];

  return (
    <>
      <div className={tickerClassName} role="region" aria-label="Supply chain news ticker">
        <NewsLabel />
        <div className="news-ticker-viewport">
          <div className="news-ticker-track">
            {loop.map((item, index) => {
              const key = `${item.link || item.title}-${index}`;
              const label = headlineLabel(item);
              const isLoadingPlaceholder = !headlines.length;
              return (
                <span key={key} className="news-ticker-item">
                  {isLoadingPlaceholder ? (
                    <span className="news-ticker-item-text">{label}</span>
                  ) : (
                    <button
                      type="button"
                      className="news-ticker-item-btn"
                      onClick={() => setSelectedHeadline(item)}
                      aria-label={`News headline: ${label}`}
                      title={`${label} — Read article or create scenario`}
                    >
                      <Globe2 size={14} className="news-ticker-icon" aria-hidden="true" />
                      <span className="news-ticker-item-text">{label}</span>
                    </button>
                  )}
                  <span className="news-ticker-sep" aria-hidden="true">
                    {SEPARATOR}
                  </span>
                </span>
              );
            })}
          </div>
        </div>
      </div>

      {selectedHeadline ? (
        <NewsHeadlineModal
          item={selectedHeadline}
          onClose={() => setSelectedHeadline(null)}
          onCreateScenario={onCreateScenarioFromNews}
        />
      ) : null}
    </>
  );
}

NewsTicker.propTypes = {
  items: PropTypes.arrayOf(
    PropTypes.shape({
      title: PropTypes.string,
      link: PropTypes.string,
      source: PropTypes.string,
      published_at: PropTypes.string,
      summary: PropTypes.string,
    }),
  ),
  loading: PropTypes.bool,
  onCreateScenarioFromNews: PropTypes.func,
  embedded: PropTypes.bool,
};

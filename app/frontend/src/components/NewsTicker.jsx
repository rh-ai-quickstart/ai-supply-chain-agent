import PropTypes from "prop-types";

const SEPARATOR = "  ·  ";

export function NewsTicker({ items = [], loading = false }) {
  const headlines = Array.isArray(items) ? items.filter((item) => item?.title) : [];

  if (!loading && headlines.length === 0) {
    return (
      <div className="news-ticker" role="status" aria-live="polite">
        <span className="news-ticker-label">News</span>
        <div className="news-ticker-track">
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
    <div className="news-ticker" role="region" aria-label="Supply chain news ticker">
      <span className="news-ticker-label">News</span>
      <div className="news-ticker-viewport">
        <div className="news-ticker-track">
          {loop.map((item, index) => {
            const key = `${item.link || item.title}-${index}`;
            const label = item.source ? `${item.source}: ${item.title}` : item.title;
            return (
              <span key={key} className="news-ticker-item">
                {item.link ? (
                  <a href={item.link} target="_blank" rel="noopener noreferrer">
                    {label}
                  </a>
                ) : (
                  <span>{label}</span>
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
};

import PropTypes from "prop-types";
import { APP_VERSION, formatBuildTime } from "../version";
import { NewsTicker } from "./NewsTicker";

export function DashboardHeader({
  isLightTheme = false,
  onToggleTheme,
  activeView = "simulation",
  onNavigate,
  newsItems = [],
  newsLoading = false,
  onCreateScenarioFromNews,
}) {
  const builtAt = formatBuildTime(APP_VERSION.buildTime);
  const showNewsTicker = activeView === "simulation";

  return (
    <header className="dashboard-header panel-lite">
      <div className="dashboard-header-main">
        <div className="dashboard-header-title">
          <h1>Supply Chain Command Center</h1>
          <span
            className="dashboard-version muted"
            title={builtAt ? `Built ${APP_VERSION.buildTime}` : undefined}
          >
            {APP_VERSION.gitCommit}
            {builtAt ? ` · built ${builtAt}` : ""}
          </span>
        </div>
        {onNavigate ? (
          <nav className="dashboard-nav" aria-label="Main">
            <button
              type="button"
              className={`dashboard-nav-btn${activeView === "simulation" ? " dashboard-nav-btn--active" : ""}`}
              onClick={() => onNavigate("simulation")}
              title="Run disruption simulations on the map"
            >
              Simulation
            </button>
            <button
              type="button"
              className={`dashboard-nav-btn${activeView === "knowledge-bases" ? " dashboard-nav-btn--active" : ""}`}
              onClick={() => onNavigate("knowledge-bases")}
              title="Upload and manage RAG document stores"
            >
              Knowledge bases
            </button>
          </nav>
        ) : null}
      </div>
      <div className="dashboard-header-aside">
        {showNewsTicker ? (
          <NewsTicker
            items={newsItems}
            loading={newsLoading}
            onCreateScenarioFromNews={onCreateScenarioFromNews}
            embedded
          />
        ) : null}
        <button
          className="theme-btn"
          type="button"
          onClick={onToggleTheme}
          aria-label="Toggle theme"
          title="Switch between light and dark theme"
        >
          {isLightTheme ? "🌙" : "☀️"}
        </button>
      </div>
    </header>
  );
}

DashboardHeader.propTypes = {
  isLightTheme: PropTypes.bool,
  onToggleTheme: PropTypes.func,
  activeView: PropTypes.string,
  onNavigate: PropTypes.func,
  newsItems: PropTypes.arrayOf(
    PropTypes.shape({
      title: PropTypes.string,
      link: PropTypes.string,
      source: PropTypes.string,
      published_at: PropTypes.string,
      summary: PropTypes.string,
    }),
  ),
  newsLoading: PropTypes.bool,
  onCreateScenarioFromNews: PropTypes.func,
};

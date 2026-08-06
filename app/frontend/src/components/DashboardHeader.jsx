import PropTypes from "prop-types";
import { APP_VERSION, formatBuildTime } from "../version";

export function DashboardHeader({ isLightTheme = false, onToggleTheme, activeView = "simulation", onNavigate }) {
  const builtAt = formatBuildTime(APP_VERSION.buildTime);
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
            >
              Simulation
            </button>
            <button
              type="button"
              className={`dashboard-nav-btn${activeView === "knowledge-bases" ? " dashboard-nav-btn--active" : ""}`}
              onClick={() => onNavigate("knowledge-bases")}
            >
              Knowledge bases
            </button>
            <button
              type="button"
              className={`dashboard-nav-btn${activeView === "create-scenario" ? " dashboard-nav-btn--active" : ""}`}
              onClick={() => onNavigate("create-scenario")}
            >
              Create scenario
            </button>
          </nav>
        ) : null}
      </div>
      <button className="theme-btn" type="button" onClick={onToggleTheme} aria-label="Toggle theme">
        {isLightTheme ? "🌙" : "☀️"}
      </button>
    </header>
  );
}

DashboardHeader.propTypes = {
  isLightTheme: PropTypes.bool,
  onToggleTheme: PropTypes.func,
  activeView: PropTypes.string,
  onNavigate: PropTypes.func,
};

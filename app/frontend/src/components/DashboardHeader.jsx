import PropTypes from "prop-types";

export function DashboardHeader({ isLightTheme = false, onToggleTheme, activeView = "dashboard", onNavigate }) {
  return (
    <header className="dashboard-header panel-lite">
      <div className="dashboard-header-main">
        <h1>Supply Chain Command Center</h1>
        {onNavigate ? (
          <nav className="dashboard-nav" aria-label="Main">
            <button
              type="button"
              className={`dashboard-nav-btn${activeView === "dashboard" ? " dashboard-nav-btn--active" : ""}`}
              onClick={() => onNavigate("dashboard")}
            >
              Dashboard
            </button>
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

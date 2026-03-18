export function DashboardHeader({ isLightTheme, onToggleTheme }) {
  return (
    <header className="dashboard-header panel-lite">
      <h1>Supply Chain Command Center</h1>
      <button className="theme-btn" type="button" onClick={onToggleTheme}>
        {isLightTheme ? "🌙" : "☀️"}
      </button>
    </header>
  );
}

export function AlertsPanel({ loading, error, alerts }) {
  return (
    <section className="panel insights-panel">
      <h3>Real-Time Alerts</h3>
      {loading && <p className="muted">Loading live state...</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !alerts.length && <p className="muted">No active alerts.</p>}

      <div className="stack">
        {alerts.slice(0, 6).map((alert, index) => (
          <div key={`${alert.type}-${index}`} className={`alert ${alert.type ?? "info"}`}>
            <strong>{(alert.type ?? "info").toUpperCase()}</strong>: {alert.text}
          </div>
        ))}
      </div>
    </section>
  );
}

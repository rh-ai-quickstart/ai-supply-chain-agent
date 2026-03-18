function HealthItem({ label, value, fillPercent, tone }) {
  return (
    <div className="health-item">
      <div className="health-item-header">
        <span className="health-label">{label}</span>
        <span className="health-value">{value}</span>
      </div>
      <div className="health-track">
        <div className={`health-fill ${tone}`} style={{ width: `${fillPercent}%` }} />
      </div>
    </div>
  );
}

export function SystemHealthPanel({ health }) {
  const supplierTone =
    health.supplierHealth >= 90 ? "good" : health.supplierHealth >= 80 ? "warn" : "bad";
  const inventoryTone =
    health.inventoryHealth >= 95 ? "good" : health.inventoryHealth >= 85 ? "warn" : "bad";
  const riskTone = health.riskIndex < 35 ? "good" : health.riskIndex < 60 ? "warn" : "bad";
  const freshnessTone =
    health.dataFreshnessPercent >= 90
      ? "good"
      : health.dataFreshnessPercent >= 50
        ? "warn"
        : "bad";

  return (
    <article className="panel chart-panel">
      <h3>System Health</h3>
      <div className="health-grid">
        <HealthItem
          label="Supplier Health"
          value={`${health.supplierHealth}%`}
          fillPercent={health.supplierHealth}
          tone={supplierTone}
        />
        <HealthItem
          label="Inventory Health"
          value={`${health.inventoryHealth}%`}
          fillPercent={health.inventoryHealth}
          tone={inventoryTone}
        />
        <HealthItem
          label="Risk Index"
          value={health.riskLabel}
          fillPercent={health.riskIndex}
          tone={riskTone}
        />
        <HealthItem
          label="Data Freshness"
          value={`${health.dataFreshnessPercent}%`}
          fillPercent={health.dataFreshnessPercent}
          tone={freshnessTone}
        />
      </div>
    </article>
  );
}

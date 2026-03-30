export function KpiBar({ kpis }) {
  return (
    <section className="kpi-bar">
      <div className="kpi-card">
        <span className="kpi-label">In-Stock Rate</span>
        <span className="kpi-value">{kpis.inStock?.value ?? "--%"}</span>
      </div>
      <div className="kpi-card">
        <span className="kpi-label">On-Time Delivery</span>
        <span className="kpi-value">{kpis.onTime?.value ?? "--%"}</span>
      </div>
      <div className="kpi-card">
        <span className="kpi-label">Inventory Turnover</span>
        <span className="kpi-value">{kpis.turnover?.value ?? "--x"}</span>
      </div>
      <div className="kpi-card">
        <span className="kpi-label">Lost Sales</span>
        <span className="kpi-value">{kpis.lostSales?.value ?? "$--M"}</span>
      </div>
      <div className="kpi-card">
        <span className="kpi-label">Optimal Reorder</span>
        <span className="kpi-value">{kpis.reorderPoint?.value ?? "--%"}</span>
      </div>
    </section>
  );
}

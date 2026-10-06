import PropTypes from "prop-types";
import { InfoTooltip } from "./InfoTooltip";
import { SUPPLY_CHAIN_KPI_DEFINITIONS } from "../utils/supplyChainKpis";

function KpiCard({ label, tooltip, value, trend, trendDirection, trendSentiment, loading }) {
  const trendClassName = [
    "kpi-trend",
    trendDirection !== "neutral" ? trendDirection : "",
    trendSentiment !== "neutral" ? `kpi-trend--${trendSentiment}` : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="kpi-card-new">
      <InfoTooltip label={`About ${label}`} content={tooltip} placement="top" />
      <div className="kpi-label">{label}</div>
      <div className="kpi-card-new__value-row">
        <span className="kpi-value-new">{loading ? "—" : value}</span>
        {!loading && trend ? <span className={trendClassName}>{trend}</span> : null}
      </div>
    </div>
  );
}

KpiCard.propTypes = {
  label: PropTypes.string.isRequired,
  tooltip: PropTypes.string.isRequired,
  value: PropTypes.string.isRequired,
  trend: PropTypes.string,
  trendDirection: PropTypes.oneOf(["up", "down", "neutral"]),
  trendSentiment: PropTypes.oneOf(["good", "bad", "caution", "neutral"]),
  loading: PropTypes.bool,
};

export function SupplyChainKpiBar({ kpis = null, loading = false, error = "" }) {
  return (
    <section className="kpi-bar" role="region" aria-label="Supply chain KPIs" aria-busy={loading}>
      {error ? (
        <p className="kpi-bar__error muted" role="status">{error}</p>
      ) : null}
      {SUPPLY_CHAIN_KPI_DEFINITIONS.map((definition) => {
        const metric = kpis?.[definition.key] ?? {};
        return (
          <KpiCard
            key={definition.key}
            label={definition.label}
            tooltip={definition.tooltip}
            value={metric.value ?? "—"}
            trend={metric.trend ?? ""}
            trendDirection={metric.trendDirection ?? "neutral"}
            trendSentiment={metric.trendSentiment ?? "neutral"}
            loading={loading}
          />
        );
      })}
    </section>
  );
}

SupplyChainKpiBar.propTypes = {
  kpis: PropTypes.object,
  loading: PropTypes.bool,
  error: PropTypes.string,
};

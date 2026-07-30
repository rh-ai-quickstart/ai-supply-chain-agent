import PropTypes from "prop-types";
import { Line } from "react-chartjs-2";

export function DemandChartPanel({ data }) {
  if (!data) {
    return (
      <article className="panel chart-panel">
        <h3>Demand Forecast</h3>
        <p className="muted">No demand data available.</p>
      </article>
    );
  }
  return (
    <article className="panel chart-panel">
      <h3>Demand Forecast</h3>
      <div className="chart-box">
        <Line data={data} options={{ maintainAspectRatio: false, responsive: true }} />
      </div>
    </article>
  );
}

DemandChartPanel.propTypes = {
  data: PropTypes.object,
};

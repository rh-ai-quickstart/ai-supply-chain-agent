import PropTypes from "prop-types";
import { Bar } from "react-chartjs-2";

export function RevenueChartPanel({ data }) {
  if (!data) {
    return (
      <article className="panel chart-panel">
        <h3>Revenue Impact</h3>
        <p className="muted">No revenue data available.</p>
      </article>
    );
  }
  return (
    <article className="panel chart-panel">
      <h3>Revenue Impact</h3>
      <div className="chart-box">
        <Bar
          data={data}
          options={{
            maintainAspectRatio: false,
            responsive: true,
            plugins: { legend: { display: false } },
          }}
        />
      </div>
    </article>
  );
}

RevenueChartPanel.propTypes = {
  data: PropTypes.object,
};

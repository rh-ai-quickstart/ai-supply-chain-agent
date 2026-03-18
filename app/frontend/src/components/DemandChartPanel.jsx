import { Line } from "react-chartjs-2";

export function DemandChartPanel({ data }) {
  return (
    <article className="panel chart-panel">
      <h3>Demand Forecast</h3>
      <div className="chart-box">
        <Line data={data} options={{ maintainAspectRatio: false, responsive: true }} />
      </div>
    </article>
  );
}

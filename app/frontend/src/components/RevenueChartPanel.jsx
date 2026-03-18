import { Bar } from "react-chartjs-2";

export function RevenueChartPanel({ data }) {
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

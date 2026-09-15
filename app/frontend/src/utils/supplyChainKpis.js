/** KPI labels and tooltips for the supply-chain KPI bar (values come from /api/v1/kpis). */

export const SUPPLY_CHAIN_KPI_DEFINITIONS = [
  {
    key: "inStock",
    label: "In-Stock Rate",
    tooltip: "SKU fill rate from seeded warehouse inventory (on-hand vs safety stock).",
  },
  {
    key: "onTime",
    label: "On-Time Delivery",
    tooltip: "Share of in-transit shipments arriving by promised ETA in simulation data.",
  },
  {
    key: "turnover",
    label: "Inventory Turnover",
    tooltip: "Annualized sales velocity vs on-hand inventory value from seeded SKUs.",
  },
  {
    key: "lostSales",
    label: "Lost Sales",
    tooltip: "Projected stockout exposure plus solver value-at-risk during disruptions.",
  },
  {
    key: "reorderPoint",
    label: "Optimal Reorder",
    tooltip: "Share of SKUs at or below reorder point in seeded warehouse inventory.",
  },
];

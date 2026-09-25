/** Currency and commodity display helpers. */

export function formatCurrency(amount, currency = "USD") {
  const value = Number(amount);
  if (!Number.isFinite(value)) {
    return `${currency} —`;
  }
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return `${currency} ${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  }
}

export function formatCommodityLabel(value) {
  if (!value) return "—";
  return String(value).replace(/_/g, " ");
}

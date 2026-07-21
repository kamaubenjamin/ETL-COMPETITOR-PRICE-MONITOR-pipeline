export function purchaseOrderNotices(order) {
  return [...(order?.validation?.findings ?? []), ...(order?.extraction_warnings ?? [])];
}

export function purchaseOrderAmount(order, value) {
  return value == null ? "-" : `${order?.currency ?? ""} ${value}`.trim();
}

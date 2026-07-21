import { AlertTriangle, CheckCircle2, ShoppingCart } from "lucide-react";
import type { PurchaseOrderLineItem, PurchaseOrderResult } from "../types/document";
import { DataTable, type DataTableColumn } from "./DataTable";
import { EmptyState } from "./EmptyState";
import { SeverityBadge } from "./SeverityBadge";
import { purchaseOrderAmount, purchaseOrderNotices } from "../state/purchaseOrderCore.mjs";

const columns: readonly DataTableColumn<PurchaseOrderLineItem>[] = [
  { key: "item", header: "Item code", render: (row) => row.item_code ?? "Not determined" },
  { key: "barcode", header: "Barcode", render: (row) => row.barcode ?? "Not determined" },
  { key: "description", header: "Description", render: (row) => row.description ?? "Not determined" },
  { key: "unit", header: "Unit", render: (row) => row.unit ?? "-" },
  { key: "quantity", header: "Quantity", render: (row) => row.quantity ?? "-" },
  { key: "price", header: "Unit price", render: (row) => row.unit_price ?? "-" },
  { key: "net", header: "Net amount", render: (row) => row.net_amount ?? "-" },
];

export function PurchaseOrderPanel({ order }: { order: PurchaseOrderResult }) {
  const notices = purchaseOrderNotices(order);
  return <section className="content-section purchase-order-panel" aria-labelledby="purchase-order-heading">
    <div className="section-heading"><div><span className="eyebrow">Canonical result</span><h2 id="purchase-order-heading"><ShoppingCart size={20} /> Purchase order</h2></div><span className="read-only-label">{order.validation.status}</span></div>
    <dl className="purchase-order-fields">
      <div><dt>Reference</dt><dd>{order.purchase_order_number ?? "Not determined"}</dd></div>
      <div><dt>Buyer</dt><dd>{order.buyer ?? "Not determined"}</dd></div>
      <div><dt>Supplier</dt><dd>{order.supplier ?? "Not determined"}</dd></div>
      <div><dt>Ship to</dt><dd>{order.ship_to ?? "Not determined"}</dd></div>
      <div><dt>Order date</dt><dd>{order.order_date ?? "Not determined"}</dd></div>
      <div><dt>Delivery date</dt><dd>{order.delivery_date ?? "Not determined"}</dd></div>
    </dl>
    <div className="purchase-order-totals"><span>Subtotal <strong>{purchaseOrderAmount(order, order.subtotal)}</strong></span><span>VAT / tax <strong>{purchaseOrderAmount(order, order.tax)}</strong></span><span>Total <strong>{purchaseOrderAmount(order, order.total)}</strong></span></div>
    {order.line_items.length ? <DataTable caption="Purchase-order line items" columns={columns} rows={order.line_items} rowKey={(row) => `${row.item_code}-${row.barcode}`} /> : <EmptyState title="No line items" message="No line items were determined safely." />}
    <div className="purchase-order-notices"><h3>{notices.length ? <AlertTriangle size={18} /> : <CheckCircle2 size={18} />} Validation and extraction</h3>{notices.length ? <ul>{notices.map((notice, index) => <li key={`${notice.code}-${notice.field}-${index}`}><SeverityBadge severity={notice.severity} /> <strong>{notice.field}</strong> — {notice.message}</li>)}</ul> : <p>No validation findings or extraction warnings.</p>}</div>
    <p className="filter-note">Source: {order.source_lineage.source_name} · {order.source_lineage.source_type} · {order.source_lineage.extraction_rule}{order.source_lineage.page_count ? ` · ${order.source_lineage.page_count} page` : ""}</p>
  </section>;
}

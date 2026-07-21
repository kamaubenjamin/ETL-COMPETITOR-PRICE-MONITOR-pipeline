import type { PurchaseOrderFinding, PurchaseOrderResult } from "../types/document";
export function purchaseOrderNotices(order: PurchaseOrderResult): PurchaseOrderFinding[];
export function purchaseOrderAmount(order: PurchaseOrderResult, value: string | null): string;

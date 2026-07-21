import assert from "node:assert/strict";
import { test } from "node:test";
import { purchaseOrderAmount, purchaseOrderNotices } from "../../src/state/purchaseOrderCore.mjs";

test("valid synthetic purchase order renders exact display amounts without notices", () => {
  const order = { currency: "KES", validation: { findings: [] }, extraction_warnings: [] };
  assert.equal(purchaseOrderAmount(order, "464.00"), "KES 464.00");
  assert.deepEqual(purchaseOrderNotices(order), []);
});

test("validation and extraction warnings are both rendered", () => {
  const validation = { severity: "error", code: "total_mismatch", field: "total", message: "Totals do not match." };
  const warning = { severity: "warning", code: "not_determined", field: "terms", message: "Terms were not determined." };
  assert.deepEqual(purchaseOrderNotices({ validation: { findings: [validation] }, extraction_warnings: [warning] }), [validation, warning]);
  assert.equal(purchaseOrderAmount({ currency: "KES" }, null), "-");
});

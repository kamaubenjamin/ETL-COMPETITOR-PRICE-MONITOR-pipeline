import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { resolve } from "node:path";
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

test("purchase-order filter and normal detail route accept the synthetic record", () => {
  const root = resolve(import.meta.dirname, "../..");
  const types = readFileSync(resolve(root, "src/types/document.ts"), "utf8");
  const documents = readFileSync(resolve(root, "src/pages/DocumentsPage.tsx"), "utf8");
  const detail = readFileSync(resolve(root, "src/pages/DocumentDetailPage.tsx"), "utf8");
  const app = readFileSync(resolve(root, "src/App.tsx"), "utf8");
  assert.match(types, /DocumentType\s*=\s*"invoice"\s*\|\s*"purchase_order"/);
  assert.match(documents, /value:\s*"purchase_order"/);
  assert.match(documents, /to=\{`\/documents\/\$\{encodeURIComponent\(row\.id\)\}`\}/);
  assert.match(app, /path="documents\/:documentId"/);
  assert.match(detail, /document\.data\.document_type === "purchase_order"/);
  assert.match(detail, /getPurchaseOrder\(client, documentId\)/);
});

test("authorized absent upload processing status renders as a neutral optional state", () => {
  const root = resolve(import.meta.dirname, "../..");
  const panel = readFileSync(resolve(root, "src/components/ProcessingStatusPanel.tsx"), "utf8");
  const detail = readFileSync(resolve(root, "src/pages/DocumentDetailPage.tsx"), "utf8");

  assert.match(panel, /failure\.status === "not_found" \? \{ status: "empty" \} : failure/);
  assert.match(panel, /Processing status is not available in this technical preview\./);
  assert.match(detail, /<ProcessingStatusPanel documentId=\{document\.id\} \/>/);
  assert.match(detail, /document\.processing\.map/);
  assert.doesNotMatch(panel, /upload_document|approve|export_document/i);
});

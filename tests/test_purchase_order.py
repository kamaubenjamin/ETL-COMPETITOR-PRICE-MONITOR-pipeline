from decimal import Decimal
from types import SimpleNamespace

from src.document_engine.classifiers.document_classifier import classify_document
from src.document_engine.contracts.document import Document, DocumentIngestionResult, DocumentSource
from src.document_engine.parsers.document_parser import DocumentParser
from src.purchase_order import (
    PurchaseOrder,
    PurchaseOrderExtractor,
    PurchaseOrderLineItem,
    SourceReference,
    classify_purchase_order,
    validate_purchase_order,
)


SYNTHETIC_TEXT = """PURCHASE ORDER
PO Number: PO-EXAMPLE-100
Order Date: 2026-07-10
Delivery Date: 2026-07-18
Buyer: Example Buyer Ltd
Supplier: Fictional Supplier Co
Ship To: Example Warehouse
Currency: KES
Item Code
Barcode
Description
Unit
Quantity
Unit Price
Net Amount
DEMO-A10
9900000000011
Fictional archive cartons with
reinforced handles
CTN
2.00
125.000000
250.00
DEMO-B20
9900000000028
Fictional document sleeves
PKT
4.00
37.500000
150.00
Sub Total
400.00
VAT
64.00
Grand Total
464.00
Terms: Fictional demonstration terms only
"""


def pipeline_for(content: str = SYNTHETIC_TEXT):
    document = Document(DocumentSource("synthetic-po.pdf", "pdf", "application/pdf"), content, {"page_count": 1})
    ingestion = DocumentIngestionResult(document, classify_document(document), document, "ingestion-synthetic")
    return SimpleNamespace(ingestion_result=ingestion, parsing_result=DocumentParser().parse(content), pipeline_run_id="run-synthetic")


def test_purchase_order_classification_uses_content_signals():
    assert classify_purchase_order(SYNTHETIC_TEXT)["document_type"] == "purchase_order"
    assert classify_document(pipeline_for().ingestion_result.document)["document_type"] == "purchase_order"
    unrelated = Document(DocumentSource("note.pdf", "pdf", "application/pdf"), "ordinary memo", {})
    assert classify_document(unrelated)["document_type"] == "pdf"


def test_extracts_headers_wrapped_descriptions_all_lines_and_exact_money():
    order = PurchaseOrderExtractor().extract(pipeline_for(), source_name="synthetic-test")
    assert order.purchase_order_number == "PO-EXAMPLE-100"
    assert (order.buyer, order.supplier, order.ship_to) == ("Example Buyer Ltd", "Fictional Supplier Co", "Example Warehouse")
    assert (order.order_date, order.delivery_date, order.currency) == ("2026-07-10", "2026-07-18", "KES")
    assert len(order.line_items) == 2
    assert order.line_items[0].description == "Fictional archive cartons with reinforced handles"
    assert [item.item_code for item in order.line_items] == ["DEMO-A10", "DEMO-B20"]
    assert order.line_items[0].unit_price == Decimal("125.000000")
    assert (order.subtotal, order.tax, order.total) == (Decimal("400.00"), Decimal("64.00"), Decimal("464.00"))
    assert order.validation and order.validation.is_valid


def test_canonical_serialization_uses_fixed_point_strings_and_safe_lineage():
    payload = PurchaseOrderExtractor().extract(pipeline_for(), source_name="synthetic-test").to_dict()
    assert payload["subtotal"] == "400.00"
    assert payload["line_items"][0]["unit_price"] == "125.000000"
    assert payload["source_lineage"]["source_name"] == "synthetic-test"
    assert "source_path" not in payload["source_lineage"]


def test_validation_reports_required_dates_numbers_and_malformed_values():
    lineage = SourceReference("synthetic", "malformed-test", "i", "r")
    item = PurchaseOrderLineItem("DUP", None, "Malformed example", "EA", Decimal("0"), Decimal("-1"), Decimal("2"), lineage)
    order = PurchaseOrder(None, None, None, None, "not-a-date", "2020-01-01", "XXX", Decimal("3"), Decimal("1"), Decimal("9"), (item, item), None, lineage)
    result = validate_purchase_order(order)
    codes = {finding.code for finding in result.findings}
    assert not result.is_valid
    assert {"required", "invalid_date", "invalid_quantity", "invalid_unit_price", "line_amount_mismatch", "subtotal_mismatch", "total_mismatch", "duplicate_item_code", "invalid_currency"} <= codes
    assert any(finding.severity == "warning" for finding in result.findings)


def test_missing_items_and_malformed_numeric_text_produce_validation_findings():
    content = SYNTHETIC_TEXT.replace("2.00", "many", 1).replace("125.000000", "unknown", 1)
    order = PurchaseOrderExtractor().extract(pipeline_for(content))
    assert order.validation and not order.validation.is_valid
    assert any(finding.code in {"invalid_quantity", "line_amount_mismatch", "required", "subtotal_mismatch"} for finding in order.validation.findings)

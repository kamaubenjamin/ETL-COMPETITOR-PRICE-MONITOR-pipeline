from src.document_engine.contracts.document import Document, DocumentSource, DocumentIngestionResult
from src.document_engine.orchestration.ingestion_pipeline import IngestionPipelineResult
from src.document_engine.structure.models.canonical_table import CanonicalTable
from src.document_engine.structure.models.parsing_result import ParsingResult
from src.entity_runtime.engine import EntityExtractionEngine
from src.entity_runtime.contracts import EntitySet


def test_entity_extraction_engine_extracts_entities_from_simple_document():
    document = Document(
        source=DocumentSource(path="/tmp/invoice.txt", source_type="text", media_type="text/plain"),
        content="""
Supplier: ABC Supplies
Address: 123 Market St
Phone: +1 555 0123
Email: contact@abc.com

Customer: Quickmart Ltd.
Address: 789 Retail Rd
Phone: +1 555 0456
Email: buyer@quickmart.com

Invoice Number: INV-1001
Invoice Date: 2026-05-01
Due Date: 2026-05-15
Currency: USD

Item Description Quantity Unit Price Line Total
SKU123 Widget A 2 25.00 50.00
SKU124 Widget B 1 15.00 15.00
Subtotal 65.00
Tax 7.80
Grand Total 72.80
""",
        metadata={"source_name": "abc_supplies"},
    )

    ingestion_result = DocumentIngestionResult(
        document=document,
        classification={"document_type": "invoice"},
        normalized_document=document,
        ingestion_id="ingest-1",
    )

    parsing_result = ParsingResult(
        blocks=[],
        sections=[
            {
                "section_type": "supplier_section",
                "start_line": 0,
                "end_line": 3,
                "content": "Supplier: ABC Supplies\nAddress: 123 Market St\nPhone: +1 555 0123\nEmail: contact@abc.com",
            },
            {
                "section_type": "customer_section",
                "start_line": 5,
                "end_line": 8,
                "content": "Customer: Quickmart Ltd.\nAddress: 789 Retail Rd\nPhone: +1 555 0456\nEmail: buyer@quickmart.com",
            },
            {
                "section_type": "line_items_section",
                "start_line": 11,
                "end_line": 12,
                "content": "Item Description Quantity Unit Price Line Total\nSKU123 Widget A 2 25.00 50.00\nSKU124 Widget B 1 15.00 15.00",
            },
            {
                "section_type": "totals_section",
                "start_line": 13,
                "end_line": 15,
                "content": "Subtotal 65.00\nTax 7.80\nGrand Total 72.80",
            },
        ],
        tables=[
            CanonicalTable(
                columns=["SKU", "Description", "Quantity", "Unit Price", "Line Total"],
                rows=[
                    ["SKU123", "Widget A", "2", "25.00", "50.00"],
                    ["SKU124", "Widget B", "1", "15.00", "15.00"],
                ],
                row_count=2,
                column_count=5,
                confidence_score=0.8,
            )
        ],
    )

    pipeline_result = IngestionPipelineResult(
        ingestion_result=ingestion_result,
        parsing_result=parsing_result,
        validation_result=None,
        quality_score=0.95,
        pipeline_run_id="run-1",
    )

    engine = EntityExtractionEngine()
    entity_set = engine.extract(pipeline_result)

    assert isinstance(entity_set, EntitySet)
    assert entity_set.source_document_id == "ingest-1"
    assert len(entity_set.suppliers) == 1
    assert entity_set.suppliers[0].name == "ABC Supplies"
    assert len(entity_set.customers) == 1
    assert entity_set.customers[0].name == "Quickmart Ltd."
    assert len(entity_set.references) == 1
    assert entity_set.references[0].document_number == "INV-1001"
    assert len(entity_set.financials) == 1
    assert entity_set.financials[0].grand_total == 72.8
    assert len(entity_set.line_items) == 2
    assert entity_set.extraction_confidence > 0

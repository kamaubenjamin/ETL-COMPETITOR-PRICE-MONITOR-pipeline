# Smart Playwright Extraction

`SmartPlaywrightConnector` is the adaptive supermarket/ecommerce ingestion connector for ETL Banking. It keeps FlowSync as the control plane and leaves all extraction behavior inside the execution plane.

## Architecture

The connector lives at `src/connectors/smart_playwright.py` and follows the standard connector lifecycle:

1. `validate()` checks URL and optional selector input.
2. `extract()` opens Playwright, scrolls, crawls pages, and collects product cards.
3. `transform()` is inherited for connector-local transforms.
4. `normalize()` emits the canonical product schema.
5. `load()` remains a no-op because workflow execution owns persistence.

The heuristic engine lives in `src/extract/heuristics/`. It supports semantic DOM analysis, repeated card detection, text density scoring, currency detection, ecommerce structures, supermarket cards, nested card handling, pagination, and infinite-scroll-style loading.

## Extraction Flow

1. Try semantic card auto-detection across common ecommerce selectors.
2. If auto-detection fails, use the workflow selector when provided.
3. If that fails, try generic ecommerce card/list heuristics.
4. Normalize extracted products into comparison-ready fields.
5. Attach extraction metrics to `DataFrame.attrs["extraction_metrics"]`.

Tracked metrics include products extracted, pages crawled, extraction confidence, fallback usage, failures, strategy, pagination depth, and duplicate collapse count.

## Canonical Product Fields

Smart extraction emits:

- `product_name`
- `normalized_name`
- `brand`
- `category`
- `source`
- `current_price`
- `old_price`
- `discount_percentage`
- `availability`
- `timestamp`
- `url`
- `image_url`
- `currency`
- `sku`
- `confidence_score`

## Workflow Examples

See:

- `workflows/naivas_detergents_monitoring.json`
- `workflows/quickmart_detergents_monitoring.json`

Naivas has a public detergent category page. Quickmart/Q SOKO may require branch/location context before product cards render, so its workflow is disabled by default until the run environment can provide that session context.

## Normalization Pipeline

`src/transforms/product_identity.py` normalizes whitespace, brands, units, sizes, and duplicate entities. For example:

- `Omo 1kg`
- `OMO 1 KG`
- `Omo Washing Powder 1kg`

normalize toward comparable product identities such as `omo 1kg`.

## Future AI Extraction Roadmap

The heuristic boundary is ready for:

- AI-assisted extraction strategy selection
- LLM-assisted product text parsing
- OCR ingestion for image-heavy catalogs
- vision-based extraction for rendered product tiles
- ERP ingestion and supplier feeds
- Kafka ingestion streams for product batches
- distributed worker execution through Celery or Airflow
- Supabase realtime or websocket telemetry fanout

Keep those additions behind connector and transform contracts so FlowSync API payloads remain backward compatible.

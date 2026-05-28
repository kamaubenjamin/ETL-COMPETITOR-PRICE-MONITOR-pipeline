# 💰 Competitor Price Monitor

## 📌 Project Overview

**Competitor Price Intelligence Platform** — A modular ETL system for monitoring competitor pricing across multiple ecommerce and retail platforms.

The platform:

* Extracts product data from multiple sources (web scraping, APIs, CSV uploads)
* Normalizes and standardizes data with intelligent parsing
* Matches products across sources using fuzzy matching and feature extraction
* Tracks price changes and historical trends
* Generates real-time alerts on price movements and undercutting
* Provides interactive dashboards for monitoring and analytics

---

## ⚙️ Tech Stack

* Python 3.11+ 🐍
* Streamlit (interactive dashboard)
* Pandas & NumPy (data processing)
* Playwright & Selenium (web scraping)
* BeautifulSoup (HTML parsing)
* RapidFuzz (fuzzy matching)
* SQLite3 (local storage)
* Requests (HTTP calls)

---

## 🔄 Pipeline Architecture

### Extract Layer
- Web scraping (Playwright, Selenium)
- CSV imports
- API connectors
- Configurable selectors and modes

### Transform Layer
- Product name normalization
- Price parsing with currency detection
- Availability status extraction
- Category classification
- Transformation rules engine

### Matching Layer
- Brand extraction
- Size/model detection
- Fuzzy matching with configurable thresholds
- Cross-source product mapping

### Monitoring Layer
- Historical price tracking
- Price change detection
- Undercut alerts
- Real-time notifications

### FlowSync Telemetry Layer
- Supabase integration lives in `src/integrations/supabase_client.py`
- Shared telemetry contracts live in `src/contracts/telemetry.py`
- Pipeline and ingestion instrumentation lives in `src/telemetry/`
- Operational alert publishing lives in `src/services/alert_manager.py`
- ETL execution writes best-effort events to `pipeline_runs`, `ingestion_logs`, and `operational_alerts`
- Telemetry is disabled automatically when Supabase credentials are missing, so local ETL remains functional

### FlowSync Environment Variables
Create a local `.env` from `.env.example` or inject these values through your production secret manager:

```bash
FLOWSYNC_SUPABASE_URL=https://your-project.supabase.co
FLOWSYNC_SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
FLOWSYNC_TELEMETRY_ENABLED=true
```

### FlowSync API Boundary
FlowSync should call the ETL engine through HTTP contracts only. The API layer lives in `src/api/app.py` and delegates to `src/services/workflow_execution_service.py`.

```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8080
```

Core endpoints:

- `POST /workflows/run` - queue or run a workflow by `workflow_id`
- `POST /workflows/create` - create declarative workflow definitions
- `GET /workflows/history` - return workflow history by `workflow_id` or `run_id`
- `GET /workflows/status/{run_id}` - poll isolated execution status
- `GET /telemetry/runs` - return API-visible run status records
- `GET /alerts` - return alert records from workflow history
- `POST /connectors/test` - validate a connector without exposing pipeline internals
- `POST /sources/sync` - trigger source-level ingestion checks
- `GET /sources/health` - inspect configured source health
- `GET /reports/latest` - return latest generated reports

### Production Execution Core
- Standard connectors live in `src/connectors/` and expose `validate()`, `extract()`, `transform()`, `normalize()`, and `load()`
- Canonical product records include `product_name`, `source`, `category`, `current_price`, `old_price`, `currency`, `availability`, `sku`, `url`, and `timestamp`
- Workflow lifecycle statuses are standardized as `pending`, `queued`, `running`, `success`, `failed`, `partial_success`, `cancelled`, and `timeout`
- Execution metadata now tracks `run_id`, `workflow_id`, timestamps, `duration_ms`, records, alerts, reports, and connector type
- Structured execution logs live in `src/core/logging/` and are scoped by run, workflow, and connector
- Transform rules live behind `src/transforms/` for rename, null handling, filters, type coercion, deduplication, and normalization
- Scheduling and API execution protect against duplicate/overlapping active workflow runs
- The current scale path is in-process concurrency first; Kafka, Celery, Airflow, websocket telemetry, Supabase realtime fanout, and distributed workers can attach to these contracts without changing FlowSync endpoint shapes
- Adaptive supermarket/ecommerce extraction is available through `smart_playwright`; see `docs/SMART_PLAYWRIGHT.md`

---

## 🚀 Quick Start

```bash
# Activate environment
source venv/bin/activate  # or .\venv\Scripts\Activate on Windows

# Run dashboard
streamlit run src/dashboard.py

# Run tests
pytest tests/ -v
```

## Project Structure

ETL Banking/src/
│
├── extract/                # Data ingestion layer
│   ├── base_connector.py
│   ├── web_scraper.py     # Web extraction connector
│   ├── file_loader.py     # CSV / file ingestion
│   └── extract.py         # Connector factory
│
├── transform/             # Data transformation layer
│   ├── transformer.py     # Core transformation logic
│
├── load/                  # Data loading layer
│   ├── load_to_csv.py
│   ├── load_to_db.py
│
├── orchestrator.py       # Pipeline engine (ETL workflow)
│
├── utils/                # Logging + helpers
│
dashboard.py              # Streamlit UI (control panel)


## 🚀 How to Run

### 1. Install dependencies

```bash
pip install pandas numpy requests beautifulsoup4
```

### 2. Run the script

```bash
python banks_project.py
```

---

## 📊 Sample Output

* Extracted clean dataset of global banks
* Market capitalization converted into multiple currencies
* Stored structured data in SQLite database
* Executed SQL queries for analysis

---

## 🧠 Key Features

* End-to-end ETL pipeline
* Web scraping with BeautifulSoup
* Data transformation with Pandas
* Multi-currency conversion
* Database integration with SQLite
* Logging for tracking execution

---

## 📌 Learning Outcomes

* Building ETL pipelines in Python
* Data extraction from web sources
* Data cleaning and transformation
* Working with databases (SQLite)
* Querying structured data using SQL

---

## 📜 License

This project is for educational purposes.

---

## ✨ Author

Built with focus on data engineering fundamentals and practical ETL workflow design.

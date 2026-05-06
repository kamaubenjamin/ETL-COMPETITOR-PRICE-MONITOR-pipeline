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

# 🏦 Largest Banks ETL Pipeline

## 📌 Project Overview

This project is a full **ETL (Extract, Transform, Load)** pipeline built using Python to process and analyze data on the largest banks globally.

The pipeline:

* Extracts data from a Wikipedia page
* Transforms market capitalization values into multiple currencies
* Loads the processed data into both a CSV file and a SQLite database
* Runs SQL queries to analyze the data

---

## ⚙️ Tech Stack

* Python 🐍
* Pandas & NumPy
* BeautifulSoup (web scraping)
* SQLite3 (database)
* Requests (HTTP calls)

---

## 🔄 ETL Pipeline Flow

### 1. Extract

* Scrapes data from:

  * List of largest banks (Wikipedia archive)
* Extracts:

  * Bank Name
  * Market Capitalization (USD)

---

### 2. Transform

* Cleans and formats data
* Converts market capitalization from USD to:

  * GBP 🇬🇧
  * EUR 🇪🇺
  * INR 🇮🇳
* Adds additional columns in:

  * Millions
  * Rounded values for readability

---

### 3. Load

* Saves transformed data to:

  * CSV file (`Largest_banks_transformed.csv`)
  * SQLite database (`Banks.db`)

---

### 4. Query & Analysis

* Runs SQL queries to:

  * Retrieve full dataset
  * Calculate average market capitalization (GBP)
  * Extract top 5 banks

---
python -m src.main

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

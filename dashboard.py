import streamlit as st
import pandas as pd
import sqlite3
from src.orchestrator import ETLPipeline
import src.config as config
from src.utils import LOG_FILE
from src.load import load_to_csv, load_to_db
from src.extract.extract import run_extraction
from src.transform.engine import TransformEngine
import time

st.set_page_config(page_title="ETL Pipeline Dashboard", layout="wide")

st.write("RUNNING FILE:", __file__)
def normalize_source_type(source_type):
    if source_type == "API (Future)":
        return "API"
    return source_type
# -----------------------------
# SESSION STATE INIT
# -----------------------------
defaults = {
    "pipeline_status": "Idle",
    "last_run_time": None,
    "error_message": "",
    "refresh_count": 0,
    "execution_time": None,
    "data": None,
    "last_log_refresh": None,
    "extract_status": "Idle",
    "transform_status": "Idle",
    "load_status": "Idle",
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -----------------------------
# DATASET SELECTION
# -----------------------------
st.markdown("## Dataset Selection")

dataset_option = st.selectbox(
    "Choose dataset",
    ["Bank Data (Default)", "Custom Dataset"]
)

selected_config = config

# -----------------------------
# PIPELINE INSTANCE (KEPT)
# -----------------------------
if "pipeline" not in st.session_state:
    st.session_state.pipeline = ETLPipeline(selected_config)
else:
    st.session_state.pipeline.config = selected_config

pipeline = st.session_state.pipeline

source_type = st.selectbox(
    "Select Data Source Type",
    ["Default (Web)", "CSV", "Upload Dataset", "API (Future)"]
)

# -----------------------------
# UPLOAD
# -----------------------------
st.markdown("### Upload Custom Dataset")

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file is not None:
    try:
        st.session_state.uploaded_df = pd.read_csv(
            uploaded_file,
            engine="python",
            on_bad_lines="skip"
        )
        st.success("Custom dataset loaded ✅")
    except Exception as e:
        st.error(f"Upload failed: {e}")

# -----------------------------
# CONTROL PANEL
# -----------------------------
st.markdown("## Control Panel")

#Custom URL input for web scraping
custom_url = None
if source_type == "Default (Web)":
    custom_url = st.text_input("Enter Target URL")
# Update config with custom URL if provided
if custom_url:
    selected_config.url = custom_url


# scraping mode options   
scrape_mode = st.selectbox(
    "Scraping Mode",
    ["Auto Detect", "Table Extraction", "Full Page Text", "Custom Selector"]
)

selector = None
if scrape_mode == "Custom Selector":
    selector = st.text_input("Enter CSS selector")

transform_option = st.selectbox(
    "Select Transformation Type",
    ["Default Transform", "Raw Pass-Through"]
)

load_option = st.selectbox(
    "Select Load Destination",
    ["CSV", "Database", "Both"]
)

# -----------------------------
# RULE BUILDER
# -----------------------------
st.markdown("## Transformation Rules Builder")

drop_nulls = st.checkbox("Drop Null Values")
filter_enabled = st.checkbox("Enable Filter")
filter_condition = st.text_input("Filter Condition")
rename_enabled = st.checkbox("Rename Columns")
old_col = st.text_input("Old Column Name")
new_col = st.text_input("New Column Name")

# -----------------------------
# PIPELINE BUTTONS
# -----------------------------
col1, col2, col3, col4 = st.columns(4)

# =============================
# FULL PIPELINE (FIXED 🔥)
# =============================
with col1:
    if st.button("🔵 Run Full Pipeline"):

        start_time = time.time()

        st.session_state.pipeline_status = "Running"
        st.session_state.error_message = ""

        try:
            progress = st.progress(0)

            clean_source_type = normalize_source_type(source_type)
            uploaded_df = st.session_state.get("uploaded_df")

            if clean_source_type == "Upload Dataset" and uploaded_df is None:
                raise Exception("Please upload a dataset first")

            # rules stay EXACTLY as you had them
            rules = []

            if drop_nulls:
                rules.append({"type": "drop_nulls"})
            if filter_enabled and filter_condition:
                rules.append({"type": "filter", "condition": filter_condition})
            if rename_enabled and old_col and new_col:
                rules.append({"type": "rename", "columns": {old_col: new_col}})

            # RUN PIPELINE
            result = pipeline.run(
                source_type=clean_source_type,
                uploaded_df=uploaded_df,
                mode=scrape_mode,
                selector=selector,
                rules=rules,
                load_option=load_option
            )

            # -----------------------
            # UI UPDATES (RESTORED DETAIL)
            # -----------------------

            progress.progress(30)
            st.session_state.extract_status = "Success"
            st.info(f"Extracted {result['extract']['rows']} rows, {result['extract']['cols']} cols")

            progress.progress(70)
            st.session_state.transform_status = "Success"
            st.info(f"Transformed {result['transform']['rows']} rows, {result['transform']['cols']} cols")

            progress.progress(100)
            st.session_state.load_status = "Success"

            st.session_state.data = result["data"]
            st.session_state.pipeline_status = "Success"
            st.session_state.execution_time = f"{result['execution_time']} sec"
            st.session_state.last_run_time = time.strftime("%Y-%m-%d %H:%M:%S")

            st.success(f"Pipeline complete ✅ Shape: {result['shape']}")

        except Exception as e:
            st.session_state.pipeline_status = "Failed"
            st.error(f"Pipeline failed ❌: {e}")
# =============================
# EXTRACT ONLY
# =============================
with col2:
    if st.button("🔵 Run Extract"):
        try:
            df = run_extraction(
                source_type=source_type,
                config=selected_config,
                uploaded_df=st.session_state.get("uploaded_df"),
                mode=scrape_mode,
                selector=selector
            )

            if df is None:
                raise Exception("No data extracted")

            st.session_state.data = df
            st.session_state.extract_status = "Success"
            st.info(f"Extracted {df.shape[0]} rows, {df.shape[1]} columns")

        except Exception as e:
            st.session_state.extract_status = "Failed"
            st.session_state.error_message = str(e)

# =============================
# TRANSFORM ONLY
# =============================
with col3:
    if st.button("🟣 Run Transform", disabled=(st.session_state.extract_status != "Success")):
        try:
            df = st.session_state.data

            rules = []
            if drop_nulls:
                rules.append({"type": "drop_nulls"})
            if filter_enabled and filter_condition:
                rules.append({"type": "filter", "condition": filter_condition})
            if rename_enabled and old_col and new_col:
                rules.append({"type": "rename", "columns": {old_col: new_col}})

            engine = TransformEngine(df)
            df = engine.apply(rules)


            st.session_state.data = df
            st.session_state.transform_status = "Success"
            st.info(f"Transformed dataset: {df.shape}")

        except Exception as e:
            st.session_state.transform_status = "Failed"
            st.session_state.error_message = str(e)

# =============================
# LOAD ONLY
# =============================
with col4:
    if st.button("🟠 Run Load", disabled=(st.session_state.transform_status != "Success")):
        try:
            df = st.session_state.data

            if load_option == "CSV":
                load_to_csv(df, config.csv_path)

            elif load_option == "Database":
                conn = sqlite3.connect(config.db_name)
                load_to_db(df, conn, config.table_name)
                conn.close()

            elif load_option == "Both":
                load_to_csv(df, config.csv_path)
                conn = sqlite3.connect(config.db_name)
                load_to_db(df, conn, config.table_name)
                conn.close()

            st.session_state.load_status = "Success"

        except Exception as e:
            st.session_state.load_status = "Failed"
            st.session_state.error_message = str(e)

# =====================================================
# PIPELINE STATUS
# =====================================================
st.markdown("## 🚦 Pipeline Status")

def status_box(label, status):
    if status == "Idle":
        st.info(f"{label}\n\n⚪ Idle")
    elif status == "Running":
        st.warning(f"{label}\n\n🟡 Running...")
    elif status == "Success":
        st.success(f"{label}\n\n🟢 Done")
    elif status == "Failed":
        st.error(f"{label}\n\n🔴 Failed")

c1, c2, c3 = st.columns(3)

with c1:
    status_box("Extract", st.session_state.extract_status)

with c2:
    status_box("Transform", st.session_state.transform_status)

with c3:
    status_box("Load", st.session_state.load_status)

# =====================================================
# METRICS
# =====================================================
st.markdown("## Metrics")

m1, m2, m3, m4 = st.columns(4)

try:
    conn = sqlite3.connect(config.db_name)
    count = pd.read_sql("SELECT COUNT(*) as count FROM Largest_banks", conn)
    conn.close()

    m1.metric("Records in DB", int(count["count"].iloc[0]))
except:
    m1.metric("Records in DB", "N/A")

m2.metric("Execution Time", st.session_state.execution_time)
m3.metric("CSV Files", "1")
m4.metric("DB Status", "OK")

# =====================================================
# LOGS
# =====================================================
st.markdown("## Logs")

if st.button("🔄 Refresh Logs"):
    st.session_state.last_log_refresh = time.strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.refresh_count += 1

st.caption(f"Last refreshed: {st.session_state.last_log_refresh}")
st.caption(f"Refresh count: {st.session_state.refresh_count}")

try:
    with open(LOG_FILE, "r") as f:
        logs = f.read()
except:
    logs = "No logs yet"

st.text_area("Logs", logs, height=300)

# =====================================================
# DATA PREVIEW
# =====================================================
st.markdown("## Data Preview")

if st.session_state.data is not None:
    st.dataframe(st.session_state.data.head())
else:
    st.info("Run pipeline to see data")
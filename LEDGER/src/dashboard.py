
import streamlit as st
import pandas as pd
import sqlite3

from src.orchestrator import ETLPipeline
import src.config as config
import time
time.sleep(0.5)
st.rerun()

st.write("APP RUNNING 🔥")
st.set_page_config(page_title="ETL Pipeline Dashboard", layout="wide")
st.write("🔥 DASHBOARD UPDATED 🔥")
st.title("🏦 ETL Pipeline Dashboard")
st.subheader("Data Engineering - Banking ETL")

if "pipeline" not in st.session_state:
    st.session_state.pipeline = ETLPipeline(config)

pipeline = st.session_state.pipeline

# -----------------------------
# CONTROL PANEL
# -----------------------------
st.markdown("## Control Panelss")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("✅ Run Full Pipeline"):
        with st.spinner("Running ETL Pipeline..."):
            pipeline.run_full_pipeline()
        st.success("Pipeline completed successfully 🚀")

with col2:
    if st.button("🔵 Run Extract"):
        pipeline.run_extract()
        st.success("Extract done")

with col3:
    if st.button("🟣 Run Transform"):
        if pipeline.df is not None:
            pipeline.run_transform()
            st.success("Transform done")
        else:
            st.error("Run extract first!")

with col4:
    if st.button("🟠 Run Load"):
        if pipeline.df is not None:
            pipeline.run_load_csv()
            pipeline.run_load_db()
            st.success("Load done")
        else:
            st.error("No data to load")

# -----------------------------
# PIPELINE STATUS
# -----------------------------
st.markdown("## Pipeline Status")

c1, c2, c3, c4 = st.columns(4)

c1.success("Extraction")
c2.success("Transformation")
c3.success("CSV Load")
c4.success("DB Load")

# -----------------------------
# METRICS
# -----------------------------
st.markdown("## Metrics")

m1, m2, m3, m4 = st.columns(4)

try:
    conn = sqlite3.connect(config.db_name)
    count = pd.read_sql("SELECT COUNT(*) as count FROM Largest_banks", conn)
    conn.close()

    m1.metric("Records in DB", int(count["count"].iloc[0]))
except:
    m1.metric("Records in DB", "N/A")

m2.metric("Execution Time", "~3 min")
m3.metric("CSV Files", "1")
m4.metric("DB Status", "OK")

# -----------------------------
# LOG OUTPUT
# -----------------------------
st.markdown("## Logs")

try:
    with open(config.LOG_FILE, "r") as f:
        logs = f.read()
except:
    logs = "No logs yet"

st.text_area("Logs", logs, height=200)

# -----------------------------
# DATA PREVIEW
# -----------------------------
st.markdown("## Data Preview")

if pipeline.df is not None:
    st.dataframe(pipeline.df.head())
else:
    st.info("Run pipeline to see data")

    st.markdown("## Dataset Schema")
    
# Display schema if available
schema = st.session_state.get("schema")

if schema:
    st.json(schema)
else:
    st.info("Run pipeline to see schema")
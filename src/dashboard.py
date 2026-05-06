"""
Competitor Price Monitor Dashboard

Main dashboard is now located at: dashboard.py (root)
This file is kept for backwards compatibility.

To run the dashboard:
    streamlit run dashboard.py

All features including workflow selection are integrated in the main dashboard.
"""

# Import and expose main dashboard
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# The main dashboard should be run from the root
print("Please run: streamlit run dashboard.py (from the project root)")


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
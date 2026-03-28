from src.extract import extract
from .transform import transform
from .load import load_to_csv, load_to_db
from .utils import log_progress, run_query
from . import config
import sqlite3

# 1. Log preliminaries
log_progress('Preliminaries complete. Initiating ETL process')

# 2. Extract
df = extract(config.url, config.table_attribs)
log_progress('Data extraction complete. Initiating Transformation process')

# 3. Transform
df = transform(df, config.exchange_rate_csv_path)
log_progress('Data transformation complete. Initiating Loading process')

# 4. Load to CSV
load_to_csv(df, config.csv_path)
log_progress('Data saved to CSV file')

# 5. Load to SQLite DB
conn = sqlite3.connect(config.db_name)
log_progress('SQL Connection initiated')

load_to_db(df, conn, config.table_name)
log_progress('Data loaded to Database as a table, Executing queries')

# 6. Run queries
run_query(f"SELECT * FROM {config.table_name}", conn)
run_query(f"SELECT AVG(MC_GBP_Million) FROM {config.table_name}", conn)
run_query(f"SELECT Name FROM {config.table_name} LIMIT 5", conn)

log_progress('Process Complete')

# 7. Close connection
conn.close()
log_progress('Server Connection closed')
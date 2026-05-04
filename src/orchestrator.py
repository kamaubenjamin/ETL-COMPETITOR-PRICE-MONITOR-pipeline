import sqlite3
import time

from src.extract.extract import run_extraction
from src.transform.engine import TransformEngine
from src.load import load_to_csv, load_to_db


class ETLPipeline:

    def __init__(self, config):
        self.config = config

    def run(self, source_type, uploaded_df=None, mode=None, selector=None,
            rules=None, load_option="CSV"):

        start_time = time.time()

        result = {
            "extract": {},
            "transform": {},
            "load": {},
            "data": None,
            "shape": None,
            "execution_time": None
        }

        # -----------------------
        # EXTRACT
        # -----------------------
        df = run_extraction(
            source_type=source_type,
            config=self.config,
            uploaded_df=uploaded_df,
            mode=mode,
            selector=selector
        )

        if df is None or df.empty:
            raise Exception("No data extracted")

        result["extract"] = {
            "rows": df.shape[0],
            "cols": df.shape[1],
            "status": "Success"
        }

        # -----------------------
        # TRANSFORM
        # -----------------------
        engine = TransformEngine(df)
        df = engine.apply(rules or [])

        result["transform"] = {
            "rows": df.shape[0],
            "cols": df.shape[1],
            "status": "Success"
        }

        # -----------------------
        # LOAD
        # -----------------------
        if load_option == "CSV":
            load_to_csv(df, self.config.csv_path)

        elif load_option == "Database":
            conn = sqlite3.connect(self.config.db_name)
            load_to_db(df, conn, self.config.table_name)
            conn.close()

        elif load_option == "Both":
            load_to_csv(df, self.config.csv_path)
            conn = sqlite3.connect(self.config.db_name)
            load_to_db(df, conn, self.config.table_name)
            conn.close()

        result["load"] = {
            "status": "Success",
            "rows": df.shape[0]
        }

        result["data"] = df
        result["shape"] = df.shape
        result["execution_time"] = round(time.time() - start_time, 2)

        return result
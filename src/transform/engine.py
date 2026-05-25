import pandas as pd
from src.transform.product_parser import extract_product_info
from src.transforms.pipeline import TransformationPipeline


class TransformEngine:

    def __init__(self, df: pd.DataFrame):
        # Work on a copy to avoid mutating original data
        self.df = df.copy()

    def apply(self, rules: list):
        """
        Parse raw content first, then apply transformation rules on structured output.
        """

        # ------------------------
        # 🔥 PRODUCT PARSER (RUN FIRST WHEN CONTENT IS AVAILABLE)
        # ------------------------
        if "content" in self.df.columns:
            try:
                parsed_df = extract_product_info(self.df)
                if isinstance(parsed_df, pd.DataFrame) and not parsed_df.empty:
                    self.df = parsed_df
            except Exception as e:
                print("Parser skipped:", e)

        # ------------------------
        # 🔧 APPLY RULES
        # ------------------------
        self.df = TransformationPipeline(self.df).apply(rules or [])

        return self.df

    # ------------------------
    # RULE FUNCTIONS
    # ------------------------

    def rename_columns(self, rule):
        self.df = self.df.rename(columns=rule.get("columns", {}))

    def drop_nulls(self, rule):
        subset = rule.get("subset")
        if subset:
            self.df = self.df.dropna(subset=subset)

    def filter_data(self, rule):
        condition = rule.get("condition")
        if condition:
            self.df = self.df.query(condition)

    def add_column(self, rule):
        col = rule.get("column")
        value = rule.get("value")
        if col:
            self.df[col] = value

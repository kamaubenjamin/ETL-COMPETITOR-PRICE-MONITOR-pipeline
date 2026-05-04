import pandas as pd


class TransformEngine:

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def apply(self, rules: list):
        for rule in rules:
            rule_type = rule.get("type")

            if rule_type == "rename":
                self.rename_columns(rule)

            elif rule_type == "drop_nulls":
                self.drop_nulls(rule)

            elif rule_type == "filter":
                self.filter_data(rule)

            elif rule_type == "add_column":
                self.add_column(rule)

        return self.df

    # ------------------------
    def rename_columns(self, rule):
        self.df = self.df.rename(columns=rule.get("columns", {}))

    def drop_nulls(self, rule):
        subset = rule.get("subset")
        self.df = self.df.dropna(subset=subset)

    def filter_data(self, rule):
        condition = rule.get("condition")
        self.df = self.df.query(condition)

    def add_column(self, rule):
        col = rule.get("column")
        value = rule.get("value")
        self.df[col] = value
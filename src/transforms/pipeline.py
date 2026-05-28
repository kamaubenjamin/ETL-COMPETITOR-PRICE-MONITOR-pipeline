from __future__ import annotations

import pandas as pd

from src.transforms.product_identity import normalize_product_frame


class TransformationPipeline:
    """
    Reusable dataframe transformation pipeline.

    The pipeline is intentionally in-process for now. Celery workers or Airflow
    DAG tasks can later call the same rule engine per batch without rewriting
    transformation semantics.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def apply(self, rules: list[dict] | None = None) -> pd.DataFrame:
        for rule in rules or []:
            rule_type = rule.get("type")
            if rule_type == "rename":
                self.rename_columns(rule.get("columns", {}))
            elif rule_type == "drop_nulls":
                self.drop_nulls(rule.get("subset"))
            elif rule_type == "filter":
                self.filter_rows(rule.get("condition"))
            elif rule_type == "type_coercion":
                self.coerce_types(rule.get("columns", {}))
            elif rule_type == "deduplicate":
                self.deduplicate(rule.get("subset"))
            elif rule_type == "normalize":
                self.normalize(
                    source=rule.get("source"),
                    url=rule.get("url"),
                )
            elif rule_type == "add_column":
                self.add_column(rule.get("column"), rule.get("value"))
        return self.df

    def rename_columns(self, columns: dict) -> None:
        self.df = self.df.rename(columns=columns or {})

    def drop_nulls(self, subset: list[str] | str | None = None) -> None:
        if subset:
            self.df = self.df.dropna(subset=subset)
        else:
            self.df = self.df.dropna()

    def filter_rows(self, condition: str | None) -> None:
        if condition:
            self.df = self.df.query(condition)

    def coerce_types(self, columns: dict[str, str]) -> None:
        for column, dtype in (columns or {}).items():
            if column not in self.df.columns:
                continue
            if dtype in {"float", "float64", "number"}:
                self.df[column] = pd.to_numeric(self.df[column], errors="coerce")
            elif dtype in {"int", "int64"}:
                self.df[column] = pd.to_numeric(self.df[column], errors="coerce").astype("Int64")
            elif dtype in {"datetime", "timestamp"}:
                self.df[column] = pd.to_datetime(self.df[column], errors="coerce")
            else:
                self.df[column] = self.df[column].astype(dtype, errors="ignore")

    def deduplicate(self, subset: list[str] | str | None = None) -> None:
        self.df = self.df.drop_duplicates(subset=subset)

    def normalize(self, source: str | None = None, url: str | None = None) -> None:
        self.df = normalize_product_frame(self.df, source=source, url=url)

    def add_column(self, column: str | None, value) -> None:
        if column:
            self.df[column] = value

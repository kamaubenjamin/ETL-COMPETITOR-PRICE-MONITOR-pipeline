import pandas as pd


def generate_alerts(changes_df: pd.DataFrame, alert_rules: list[dict] | None = None):
    """
    Convert price changes into actionable alerts using workflow alert rules.
    """

    alerts = []

    if changes_df.empty:
        return ["No price changes detected"]

    if alert_rules is None:
        for _, row in changes_df.iterrows():
            if pd.isna(row["old_price"]) or pd.isna(row["new_price"]):
                continue

            try:
                old = float(row["old_price"])
                new = float(row["new_price"])
            except (ValueError, TypeError):
                continue

            if new < old:
                alerts.append(
                    f"🚨 UNDERCUT ALERT | {row['source']} lowered {row['product']} "
                    f"from {row['old_price']} → {row['new_price']}"
                )
            else:
                alerts.append(
                    f"⬆️ PRICE INCREASE | {row['product']} | {row['source']} | "
                    f"{row['old_price']} → {row['new_price']}"
                )

        return alerts

    for _, row in changes_df.iterrows():
        if pd.isna(row["old_price"]) or pd.isna(row["new_price"]):
            continue

        try:
            old = float(row["old_price"])
            new = float(row["new_price"])
        except (ValueError, TypeError):
            continue

        diff = old - new

        if diff > 0:
            for rule in alert_rules:
                if rule.get("type") == "price_drop" and diff >= rule.get("threshold", 0):
                    alerts.append(
                        f"🚨 PRICE DROP | {row['product']} | {row['source']} | "
                        f"{row['old_price']} → {row['new_price']} (drop {diff})"
                    )
                elif rule.get("type") == "undercut" and diff >= rule.get("threshold", 0):
                    alerts.append(
                        f"🚨 UNDERCUT | {row['source']} undercut {row['product']} by {diff} "
                        f"({row['old_price']} → {row['new_price']})"
                    )
        elif diff < 0:
            for rule in alert_rules:
                if rule.get("type") == "price_increase" and (-diff) >= rule.get("threshold", 0):
                    alerts.append(
                        f"⬆️ PRICE INCREASE | {row['product']} | {row['source']} | "
                        f"{row['old_price']} → {row['new_price']} (up {abs(diff)})"
                    )

    if not alerts:
        return ["No alerts triggered by workflow rules"]

    return alerts


class AlertEngine:
    """Standard alert engine for price, product, and stock monitoring."""

    def __init__(self, rules: list[dict] | None = None):
        self.rules = rules or []

    def evaluate(self, df: pd.DataFrame) -> list[dict]:
        if df is None or df.empty:
            return []

        alerts: list[dict] = []
        rules = self.rules or [
            {"type": "price_drop", "threshold": 0},
            {"type": "abnormal_spike", "threshold_percent": 50},
            {"type": "missing_product"},
            {"type": "stock_disappearance"},
        ]

        for _, row in df.iterrows():
            for rule in rules:
                alert = self._evaluate_rule(row, rule)
                if alert:
                    alerts.append(alert)
        return alerts

    def _evaluate_rule(self, row: pd.Series, rule: dict) -> dict | None:
        rule_type = rule.get("type")
        old_price = self._float(row.get("old_price"))
        new_price = self._float(row.get("new_price", row.get("current_price")))
        product = row.get("product") or row.get("product_name")
        source = row.get("source")

        if rule_type in {"price_drop", "undercut"} and old_price is not None and new_price is not None:
            drop = old_price - new_price
            threshold = float(rule.get("threshold", 0))
            if drop > 0 and drop >= threshold:
                return self._alert("price_drop", "warning", product, source, f"Price dropped by {drop}", row)

        if rule_type == "abnormal_spike" and old_price is not None and new_price is not None and old_price > 0:
            spike_percent = ((new_price - old_price) / old_price) * 100
            threshold_percent = float(rule.get("threshold_percent", rule.get("threshold", 50)))
            if spike_percent >= threshold_percent:
                return self._alert("abnormal_spike", "warning", product, source, f"Price spiked {spike_percent:.1f}%", row)

        if rule_type == "missing_product" and pd.isna(product):
            return self._alert("missing_product", "warning", product, source, "Product name is missing", row)

        if rule_type == "stock_disappearance":
            availability = str(row.get("availability", "")).lower()
            old_availability = str(row.get("old_availability", "")).lower()
            if old_availability in {"in_stock", "available", "true"} and availability in {"out_of_stock", "unavailable", "false"}:
                return self._alert("stock_disappearance", "critical", product, source, "Product disappeared from stock", row)

        if rule_type == "threshold" and new_price is not None:
            min_price = rule.get("min")
            max_price = rule.get("max")
            if min_price is not None and new_price < float(min_price):
                return self._alert("threshold", "warning", product, source, f"Price below threshold {min_price}", row)
            if max_price is not None and new_price > float(max_price):
                return self._alert("threshold", "warning", product, source, f"Price above threshold {max_price}", row)

        return None

    def _alert(self, alert_type, severity, product, source, message, row):
        return {
            "alert_type": alert_type,
            "severity": severity,
            "product_name": product,
            "source": source,
            "message": message,
            "current_price": row.get("current_price", row.get("new_price")),
            "old_price": row.get("old_price"),
            "timestamp": row.get("timestamp"),
        }

    def _float(self, value):
        try:
            if pd.isna(value):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

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
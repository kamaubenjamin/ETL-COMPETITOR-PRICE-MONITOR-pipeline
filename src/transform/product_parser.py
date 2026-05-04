import re
import pandas as pd


def extract_product_info(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract product name, price, currency, and availability
    from semi-structured scraped text.
    """

    results = []

    for row in df.iloc[:, 0]:
        text = str(row)

        # -----------------------------
        # 💰 PRICE + CURRENCY
        # -----------------------------
        price_match = re.search(r"(£|\$|KSh)?\s?(\d+[.,]?\d*)", text)

        price = None
        currency = None

        if price_match:
            currency = price_match.group(1)
            try:
                price = float(price_match.group(2).replace(",", ""))
            except:
                price = None

        # -----------------------------
        # 📦 AVAILABILITY
        # -----------------------------
        availability = ""

        lower_text = text.lower()
        if "in stock" in lower_text:
            availability = "In stock"
        elif "out of stock" in lower_text:
            availability = "Out of stock"

        # -----------------------------
        # 🏷️ PRODUCT NAME
        # -----------------------------
        name = text

        if price_match:
            name = text[:price_match.start()].strip()

        # Clean junk phrases
        name = (
            name.replace("Add to basket", "")
                .replace("add to basket", "")
                .strip()
        )

        # Skip weak rows
        if len(name) < 3:
            continue

        results.append({
            "product_name": name,
            "price": price,
            "currency": currency,
            "availability": availability
        })

    return pd.DataFrame(results)
import pandas as pd
from src.transform.comparison_engine import combine_datasets, match_products

# 🔥 Simulated datasets (like Jumia + another site)
df_jumia = pd.DataFrame({
    "product_name": [
        "Samsung 43 inch Smart TV",
        "Vitron 32 inch TV",
        "Amtec Speaker"
    ],
    "price": [34000, 12000, 5000],
    "currency": ["KES", "KES", "KES"]
})

df_kilimall = pd.DataFrame({
    "product_name": [
        "Samsung 43\" TV",
        "Vitron 32\" Smart TV",
        "Amtec Multimedia Speaker"
    ],
    "price": [35500, 11500, 5200],
    "currency": ["KES", "KES", "KES"]
})

# 🔥 Combine datasets
combined = combine_datasets({
    "jumia": df_jumia,
    "kilimall": df_kilimall
})

# 🔥 Match products
matched = match_products(combined)

print(matched)
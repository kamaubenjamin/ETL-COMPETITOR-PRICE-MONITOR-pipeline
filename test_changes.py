import pandas as pd
from src.storage.history_store import detect_price_changes

df = pd.read_csv("price_history.csv")

changes = detect_price_changes(df)

print("\n=== PRICE CHANGES ===\n")
print(changes)
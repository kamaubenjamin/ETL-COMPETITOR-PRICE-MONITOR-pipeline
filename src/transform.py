print("transform module starting...")
import pandas as pd
import numpy as np

def transform(df, exchange_rate_csv_path):
    exchange_df = pd.read_csv(exchange_rate_csv_path)
    exchange_rate = dict(zip(exchange_df.iloc[:,0], exchange_df.iloc[:,1].astype(float)))

    df['MC_USD_Billion'] = df['MC_USD_Billion'].str.replace(',', '').astype(float)

    df['MC_USD_Million'] = df['MC_USD_Billion'] * 1000
    df['MC_GBP_Million'] = np.round(df['MC_USD_Billion'] * exchange_rate['GBP'] * 1000, 2)
    df['MC_EUR_Million'] = np.round(df['MC_USD_Billion'] * exchange_rate['EUR'] * 1000, 2)
    df['MC_INR_Million'] = np.round(df['MC_USD_Billion'] * exchange_rate['INR'] * 1000, 2)

    return df
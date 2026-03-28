def load_to_csv(df, csv_path):
    df.to_csv(csv_path, index=False)


def load_to_db(df, conn, table_name):
    df.to_sql(table_name, conn, if_exists='replace', index=False)
import pandas as pd

def standardize_columns(df: pd.DataFrame):
    df.columns = (
        df.columns
        .str.strip()
        .str.replace(" ", "_")
        .str.replace(r"[^A-Za-z0-9_]", "", regex=True)
        .str.lower()
    )
    return df

def normalize_awc_code(df, col="awc_code"):
    df[col] = df[col].astype(str).str.zfill(11)
    return df

def fill_missing(df, strategy="zero"):
    if strategy == "zero":
        return df.fillna(0)
    if strategy == "ffill":
        return df.ffill()
    return df

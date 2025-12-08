import pandas as pd

def standardize_column_names(df: pd.DataFrame):
    """
    Normalize column names:
    - lower case
    - replace spaces with underscores
    - strip whitespace
    """
    df = df.copy()
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(" ", "_")
                  .str.replace("__", "_")
    )
    return df


def basic_clean(df: pd.DataFrame):
    """
    Apply basic cleaning:
    - strip whitespace in string columns
    - drop full-duplicate rows
    """
    df = standardize_column_names(df)

    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype(str).str.strip()

    df = df.drop_duplicates()

    return df


def clean_all(raw_dict: dict):
    """
    Process all loaded files with a safe, generic cleaning pipeline.
    raw_dict = {"filename": DataFrame, ...}
    Returns cleaned_dict with same keys.
    """
    cleaned = {}

    for name, df in raw_dict.items():
        print(f"[CLEANER] Cleaning {name} ...")
        cleaned[name] = basic_clean(df)

    print(f"[CLEANER] Cleaned {len(cleaned)} tables.")
    return cleaned

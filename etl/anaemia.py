from etl.loader import load_file
import pandas as pd

def analyze_anaemia(path: str) -> pd.DataFrame:
    """Load and compute anaemia indicators for PW, LM, and Children."""

    print("\n=== Anaemia Report Analysis ===")

    df = load_file(path)

    # Standardize column names early
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(" ", "_")
                  .str.replace("__", "_")
    )

    # Rename columns to predictable internal names
    df = df.rename(columns={
        "anaemic": "anaemic_pw",
        "anaemic.1": "anaemic_lm",
        "anaemic.2": "anaemic_child",

        "haemoglobin_measured_of_pw": "hb_measured_pw",
        "haemoglobin_measured_of_lm": "hb_measured_lm",
        "haemoglobin_measured_of_children_(6months_-_5_years)": "hb_measured_child",

        "district": "district"
    })

    # --- Calculated Metrics ---

    # PW anaemia %
    df["pw_anaemia_rate"] = (
        df["anaemic_pw"] / df["hb_measured_pw"].replace(0, pd.NA)
    )
    df["pw_anaemia_rate"] = (
        pd.to_numeric(df["pw_anaemia_rate"], errors="coerce")
        .fillna(0)
        .round(2)
    )

    # LM anaemia %
    df["lm_anaemia_rate"] = (
        df["anaemic_lm"] / df["hb_measured_lm"].replace(0, pd.NA)
    )
    df["lm_anaemia_rate"] = (
        pd.to_numeric(df["lm_anaemia_rate"], errors="coerce")
        .fillna(0)
        .round(2)
    )

    # Child anaemia %
    df["child_anaemia_rate"] = (
        df["anaemic_child"] / df["hb_measured_child"].replace(0, pd.NA)
    )
    df["child_anaemia_rate"] = (
        pd.to_numeric(df["child_anaemia_rate"], errors="coerce")
        .fillna(0)
        .round(2)
    )

    # Clean district names
    df["district"] = (
        df["district"]
        .astype(str)
        .str.strip()
        .str.title()
    )

    return df

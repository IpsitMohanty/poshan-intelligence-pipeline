from etl.loader import load_file
import pandas as pd

def analyze_lbw(path: str) -> pd.DataFrame:
    """Analyze Low Birth Weight indicators at district level."""

    print("\n=== Low Birth Weight (LBW) Analysis ===")

    # Load CSV
    df = load_file(path)

    # Standardize columns
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(" ", "_")
                  .str.replace("-", "_")
                  .str.replace("__", "_")
    )

    # Rename to clean internal names
    df = df.rename(columns={
        "district": "district",
        "total_children_0_6m": "total_children_0_6m",
        "low_birth_weight_children_0_6m": "lbw_children_0_6m",
    })

    # Safety check
    if "total_children_0_6m" not in df.columns or "lbw_children_0_6m" not in df.columns:
        raise KeyError("Required LBW columns not found in the dataset.")

    # LBW Rate (%)
    df["lbw_rate_pct"] = (
        df["lbw_children_0_6m"] / df["total_children_0_6m"].replace(0, pd.NA)
    )
    df["lbw_rate_pct"] = (
        pd.to_numeric(df["lbw_rate_pct"], errors="coerce")
          .fillna(0)
          .round(2)
    )

    # Standardize district names
    df["district"] = (
        df["district"]
        .astype(str)
        .str.strip()
        .str.title()
    )

    return df

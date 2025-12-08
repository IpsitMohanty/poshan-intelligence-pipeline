from etl.loader import load_file
import pandas as pd

def analyze_me(path: str) -> pd.DataFrame:
    """Analyze Measuring Efficiency for children 0–6 years."""

    print("\n=== Measuring Efficiency (0–6 years) Analysis ===")

    df = load_file(path)

    # Clean column names to match ETL output
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(" ", "_")
                  .str.replace("%", "pct")
                  .str.replace("__", "_")
    )

    # Rename for clarity
    df = df.rename(columns={
        "district": "district",
        "total_active_children": "children_total",
        "total_active_children_measured": "children_measured",
        "pct_children_measured": "children_measured_pct",
        "aww_completed_80pct_of_me": "aww_completed_80pct_me"
    })

    # --- Derived Indicators ---

    # Measurement Coverage % (recompute to be safe)
    df["measurement_coverage_pct"] = (
        df["children_measured"] / df["children_total"]
    ).replace([float("inf"), -float("inf")], 0).fillna(0).round(2)

    # AWW 80% ME Share %
    df["aww_80pct_me_share"] = (
        df["aww_completed_80pct_me"] / df["aww_completed_80pct_me"].sum()
    ).replace([float("inf"), -float("inf")], 0).fillna(0).round(2)

    # Standardize District
    df["district"] = df["district"].astype(str).str.strip().str.title()

    return df

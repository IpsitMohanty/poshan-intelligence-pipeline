from etl.loader import load_file
import pandas as pd

def analyze_home_visit(path: str) -> pd.DataFrame:
    """Analyze Home Visit performance for districts."""

    print("\n=== Home Visit Analysis ===")

    df = load_file(path)

    # Clean & standardize column names
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(" ", "_")
                  .str.replace("__", "_")
    )

    df = df.rename(columns={

        "district": "district",

        # AWW count
        "total_aww_between_01_-_30_nov,_2025": "total_aww",

        # Visit targets & performance
        "total_targeted_visits_between_01_-_30_nov,_2025": "target_visits",
        "total_visits_made_between_01_-_30_nov,_2025": "visits_made",
        "%_of_visits_made_between_01_-_30_nov,_2025": "visit_coverage_pct",

        # AWW who completed 60% HV
        "aww_completed_60%_hv_between_01_-_30_nov,_2025": "aww_60pct_hv"
    })

    # --- Derived Indicators ---

    # Visit Coverage (%)
    df["visit_coverage_pct"] = pd.to_numeric(df["visit_coverage_pct"],
                                             errors="coerce").fillna(0).round(2)

    # AWW achieving 60% HV (%)
    df["aww_60pct_hv_pct"] = (
        df["aww_60pct_hv"] / df["total_aww"].replace(0, pd.NA)
    )
    df["aww_60pct_hv_pct"] = (
        pd.to_numeric(df["aww_60pct_hv_pct"], errors="coerce")
        .fillna(0)
        .round(2)
    )

    # Standardize district naming
    df["district"] = df["district"].astype(str).str.strip().str.title()

    return df

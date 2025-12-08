from etl.loader import load_file
import pandas as pd

def analyze_awc_summary(path: str) -> pd.DataFrame:
    """Analyze AWC operational status and infrastructure readiness."""

    print("\n=== AWC Summary Analysis ===")

    df = load_file(path)

    # Clean and normalize column names
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(" ", "_")
                  .str.replace("__", "_")
    )

    df = df.rename(columns={

        "district": "district",

        "total_awc": "total_awc",
        "total_active_awc": "active_awc",
        "total_inactive_awc": "inactive_awc",
        "newly_added_awc_during_month": "new_awc_month",
        "inactive_awc_during_month": "inactive_awc_month"
    })

    # --- DERIVED INDICATORS ---

    # % active AWC
    df["active_awc_pct"] = (
        df["active_awc"] / df["total_awc"].replace(0, pd.NA)
    ).fillna(0).round(2)

    # % inactive AWC
    df["inactive_awc_pct"] = (
        df["inactive_awc"] / df["total_awc"].replace(0, pd.NA)
    ).fillna(0).round(2)

    # Churn rate: AWC opening/closing movement
    df["awc_churn_rate"] = (
        (df["new_awc_month"] + df["inactive_awc_month"]) / df["total_awc"].replace(0, pd.NA)
    ).fillna(0).round(3)

    # Operational readiness score (custom indicator)
    df["awc_readiness_score"] = (
        df["active_awc_pct"] * 0.8 + (1 - df["inactive_awc_pct"]) * 0.2
    ).round(3)

    # Clean district names
    df["district"] = df["district"].astype(str).str.strip().str.title()

    return df

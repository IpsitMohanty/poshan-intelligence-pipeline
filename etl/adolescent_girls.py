from etl.loader import load_file
import pandas as pd

def analyze_adolescent_girls(path: str) -> pd.DataFrame:
    """Analyze indicators for Adolescent Girls (14–18 years)."""

    print("\n=== Adolescent Girls (14–18) Analysis ===")

    df = load_file(path)

    # Standardize column names
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(" ", "_")
                  .str.replace("(", "")
                  .str.replace(")", "")
                  .str.replace("%", "pct")
                  .str.replace("__", "_")
    )

    # Rename to internal consistent names
    df = df.rename(columns={
        "district": "district",
        "total_active_ag": "total_ag",
        "active_ag_measured_height_&_weight": "ag_measured",
        "active_ag_measured_height__weight": "ag_measured",
        "active_ag_measured_height_weight": "ag_measured",

        "pct_of_ag_measured": "ag_measured_pct",

        "severely_thin": "ag_severely_thin",
        "thin": "ag_thin",
        "normal": "ag_normal",
        "overweight": "ag_overweight",
        "obese": "ag_obese",

        "haemoglobin_measured": "ag_hb_measured",
        "anaemic": "ag_anaemic",
    })

    # -------- Handle Measurement Indicators --------

    # AG Measurement Coverage % (if not given, compute it)
    if "ag_measured_pct" not in df.columns:
        df["ag_measured_pct"] = (
            df["ag_measured"] / df["total_ag"].replace(0, pd.NA)
        )
        df["ag_measured_pct"] = (
            pd.to_numeric(df["ag_measured_pct"], errors="coerce").fillna(0).round(2)
        )
    else:
        # Convert given % to numeric
        df["ag_measured_pct"] = (
            pd.to_numeric(df["ag_measured_pct"], errors="coerce")
            .fillna(0)
            .round(2)
        )

    # -------- Underweight Indicators --------

    # Severely Thin + Thin = Underweight
    df["ag_underweight"] = (
        df["ag_severely_thin"].fillna(0) + df["ag_thin"].fillna(0)
    )

    df["ag_underweight_pct"] = (
        df["ag_underweight"] / df["total_ag"].replace(0, pd.NA)
    )
    df["ag_underweight_pct"] = (
        pd.to_numeric(df["ag_underweight_pct"], errors="coerce").fillna(0).round(2)
    )

    # -------- Anaemia Rate --------

    df["ag_anaemia_rate"] = (
        df["ag_anaemic"] / df["ag_hb_measured"].replace(0, pd.NA)
    )
    df["ag_anaemia_rate"] = (
        pd.to_numeric(df["ag_anaemia_rate"], errors="coerce").fillna(0).round(2)
    )

    # -------- Clean district --------
    df["district"] = df["district"].astype(str).str.strip().str.title()

    return df

from etl.loader import load_file
import pandas as pd

def analyze_gm_0_5(path: str) -> pd.DataFrame:
    """Analyze Growth Monitoring for children aged 0–5 years."""

    print("\n=== Growth Monitoring (0–5 Years) Analysis ===")

    df = load_file(path)

    # Standardize column names early
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(" ", "_")
                  .str.replace("__", "_")
    )

    # Rename to consistent internal names
    df = df.rename(columns={
        "district": "district",

        "total_active_children_registered_in_the_awc_for_the_month":
            "total_children_0_5",

        "total_active_children_measured_(height_&_weight)_for_the_month":
            "measured_children_0_5",

        "measurement_efficiency_(%)":
            "measurement_efficiency_0_5",

        "severely_stunted_(n)": "stunted_severe_n_0_5",
        "severely_stunted_(%)": "stunted_severe_pct_0_5",

        "moderately_stunted_(n)": "stunted_moderate_n_0_5",
        "moderately_stunted_(%)": "stunted_moderate_pct_0_5",

        "not_stunted_(n)": "stunted_normal_n_0_5",
        "not_stunted_(%)": "stunted_normal_pct_0_5",

        "severely_underweight_(n)": "underweight_severe_n_0_5",
        "severely_underweight_(%)": "underweight_severe_pct_0_5",

        "moderately_underweight_(n)": "underweight_moderate_n_0_5",
        "moderately_underweight_(%)": "underweight_moderate_pct_0_5",

        "not_underweight_(n)": "underweight_normal_n_0_5",
        "not_underweight_(%)": "underweight_normal_pct_0_5",
    })

    # Derived indicators (lowercase)
    df["stunting_total_pct_0_5"] = (
        df["stunted_severe_pct_0_5"] + df["stunted_moderate_pct_0_5"]
    ).round(2)

    df["underweight_total_pct_0_5"] = (
        df["underweight_severe_pct_0_5"] + df["underweight_moderate_pct_0_5"]
    ).round(2)

    df["measurement_coverage_pct_0_5"] = (
        df["measured_children_0_5"] / df["total_children_0_5"] * 100
    ).round(2)

    df["normal_stunting_ratio_0_5"] = (
        df["stunted_normal_pct_0_5"] / df["stunting_total_pct_0_5"]
    ).replace([float("inf"), -float("inf")], 0).round(2)

    df["normal_underweight_ratio_0_5"] = (
        df["underweight_normal_pct_0_5"] / df["underweight_total_pct_0_5"]
    ).replace([float("inf"), -float("inf")], 0).round(2)

    # Clean district names
    df["district"] = df["district"].astype(str).str.strip().str.title()

    return df

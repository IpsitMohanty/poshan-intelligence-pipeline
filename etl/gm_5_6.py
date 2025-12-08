from etl.loader import load_file
import pandas as pd

def analyze_gm_5_6(path: str) -> pd.DataFrame:
    """Analyze Growth Monitoring for children aged 5–6 years."""

    print("\n=== Growth Monitoring (5–6 Years) Analysis ===")

    df = load_file(path)

    # Clean column names early
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(" ", "_")
                  .str.replace("__", "_")
    )

    # Standardized renaming → convert original verbose names to short names (also lowercase)
    df = df.rename(columns={
        "total_active_children_registered_in_the_awc_for_the_month": "total_children",
        "total_active_children_measured_(height_&_weight)_for_the_month": "measured_children",
        "measurement_efficiency_(%)": "measurement_efficiency",
        "severely_stunted_(n)": "stunted_severe_n",
        "severely_stunted_(%)": "stunted_severe_pct",
        "moderately_stunted_(n)": "stunted_moderate_n",
        "moderately_stunted_(%)": "stunted_moderate_pct",
        "not_stunted_(n)": "stunted_normal_n",
        "not_stunted_(%)": "stunted_normal_pct",
        "severely_underweight_(n)": "underweight_severe_n",
        "severely_underweight_(%)": "underweight_severe_pct",
        "moderately_underweight_(n)": "underweight_moderate_n",
        "moderately_underweight_(%)": "underweight_moderate_pct",
        "not_underweight_(n)": "underweight_normal_n",
        "not_underweight_(%)": "underweight_normal_pct",
    })

    # Core indicators
    df["stunting_total_pct"] = (
        df["stunted_severe_pct"] + df["stunted_moderate_pct"]
    ).round(2)

    df["underweight_total_pct"] = (
        df["underweight_severe_pct"] + df["underweight_moderate_pct"]
    ).round(2)

    df["measurement_coverage_pct"] = (
        df["measured_children"] / df["total_children"] * 100
    ).round(2)

    # Additional ratios
    df["normal_stunting_ratio"] = (
        df["stunted_normal_pct"] / df["stunting_total_pct"]
    ).replace([float("inf"), -float("inf")], 0).round(2)

    df["normal_underweight_ratio"] = (
        df["underweight_normal_pct"] / df["underweight_total_pct"]
    ).replace([float("inf"), -float("inf")], 0).round(2)

    return df

# visuals.py

import os
from analytics.visualize import (
    load_cube,
    plot_top_bottom_bar,
    plot_scatter,
    plot_corr_heatmap,
    export_bi_subset,
)

CUBE_PATH = "district_cube_2025_11.csv"
BI_EXPORT_PATH = "bi_subset_2025_11.csv"

print("\n=== Running Visual Dashboards ===\n")


def main():

    # Load cube
    cube = load_cube(CUBE_PATH)
    print(f"[DEBUG] Cube loaded: {len(cube)} rows, {len(cube.columns)} columns")

    # ------------------------------------------------------------
    # 1️⃣ TOP/BOTTOM — STUNTING (Both Age Bands)
    # ------------------------------------------------------------
    stunting_cols = [
        "Stunting_Total_%",          # GM 5–6
        "Stunting_Total_Pct_0_5"     # GM 0–5
    ]

    for col in stunting_cols:
        if col in cube.columns:
            print(f"[DEBUG] Plotting Stunting Top/Bottom for {col}...")
            plot_top_bottom_bar(cube, col)

    # ------------------------------------------------------------
    # 2️⃣ TOP/BOTTOM — UNDERWEIGHT (Both Age Bands)
    # ------------------------------------------------------------
    under_cols = [
        "Underweight_Total_%",        # GM 5–6
        "Underweight_Total_Pct_0_5"   # GM 0–5
    ]

    for col in under_cols:
        if col in cube.columns:
            print(f"[DEBUG] Plotting Underweight Top/Bottom for {col}...")
            plot_top_bottom_bar(cube, col)

    # ------------------------------------------------------------
    # 3️⃣ SCATTER — ME vs STUNTING (Both Age Bands)
    # ------------------------------------------------------------
    scatter_pairs = [
        ("Measurement_Efficiency", "Stunting_Total_%"),                 # GM 5–6
        ("Measurement_Coverage_Pct_0_5", "Stunting_Total_Pct_0_5"),     # GM 0–5
    ]

    for x, y in scatter_pairs:
        if x in cube.columns and y in cube.columns:
            print(f"[DEBUG] Plotting Scatter: {y} vs {x}")
            plot_scatter(cube, x, y)

    # ------------------------------------------------------------
    # 4️⃣ Scatter — Anaemia vs LBW
    # ------------------------------------------------------------
    if "PW_Anaemia_Rate" in cube.columns and "LBW_Rate_%" in cube.columns:
        print("[DEBUG] Plotting Anaemia vs LBW Scatter...")
        plot_scatter(cube, "PW_Anaemia_Rate", "LBW_Rate_%")

    # ------------------------------------------------------------
    # 5️⃣ CORRELATION HEATMAP — Both GM Age Bands + Key Indicators
    # ------------------------------------------------------------
    heat_cols = [
        # GM 5–6
        "Stunting_Total_%",
        "Underweight_Total_%",
        "Measurement_Efficiency",
        "Measurement_Coverage_%",

        # GM 0–5
        "Stunting_Total_Pct_0_5",
        "Underweight_Total_Pct_0_5",
        "Measurement_Coverage_Pct_0_5",

        # Supporting Indicators
        "LBW_Rate_%",
        "PW_Anaemia_Rate",
        "AG_Anaemia_%",
        "Optimum_WG_Latest_%",
        "HV_Percentage",
        "Active_AWC_%",
    ]

    heat_cols = [c for c in heat_cols if c in cube.columns]

    if len(heat_cols) > 2:
        print("[DEBUG] Plotting Heatmap...")
        plot_corr_heatmap(cube, heat_cols)
    else:
        print("[WARN] Not enough columns to plot heatmap.")

    # ------------------------------------------------------------
    # 6️⃣ EXPORT BI SUBSET
    # ------------------------------------------------------------
    print("[DEBUG] Exporting BI subset...")
    export_bi_subset(cube, BI_EXPORT_PATH)

    print("\n=== ALL PLOTS GENERATED SUCCESSFULLY ===\n")


if __name__ == "__main__":
    main()

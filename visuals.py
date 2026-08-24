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
        "stunting_total_pct",          # GM 5–6
        "stunting_total_pct_0_5"       # GM 0–5
    ]

    for col in stunting_cols:
        if col in cube.columns:
            print(f"[DEBUG] Plotting Stunting Top/Bottom for {col}...")
            plot_top_bottom_bar(cube, col)

    # ------------------------------------------------------------
    # 2️⃣ TOP/BOTTOM — UNDERWEIGHT (Both Age Bands)
    # ------------------------------------------------------------
    under_cols = [
        "underweight_total_pct",        # GM 5–6
        "underweight_total_pct_0_5"     # GM 0–5
    ]

    for col in under_cols:
        if col in cube.columns:
            print(f"[DEBUG] Plotting Underweight Top/Bottom for {col}...")
            plot_top_bottom_bar(cube, col)

    # ------------------------------------------------------------
    # 3️⃣ SCATTER — ME vs STUNTING (Both Age Bands)
    # ------------------------------------------------------------
    scatter_pairs = [
        ("measurement_efficiency", "stunting_total_pct"),                 # GM 5–6
        ("measurement_coverage_pct_0_5", "stunting_total_pct_0_5"),       # GM 0–5
    ]

    for x, y in scatter_pairs:
        if x in cube.columns and y in cube.columns:
            print(f"[DEBUG] Plotting Scatter: {y} vs {x}")
            plot_scatter(cube, x, y)

    # ------------------------------------------------------------
    # 4️⃣ Scatter — Anaemia vs LBW
    # ------------------------------------------------------------
    if "pw_anaemia_rate" in cube.columns and "lbw_rate_pct" in cube.columns:
        print("[DEBUG] Plotting Anaemia vs LBW Scatter...")
        plot_scatter(cube, "pw_anaemia_rate", "lbw_rate_pct")

    # ------------------------------------------------------------
    # 5️⃣ CORRELATION HEATMAP — Both GM Age Bands + Key Indicators
    # ------------------------------------------------------------
    heat_cols = [
        # GM 5–6
        "stunting_total_pct",
        "underweight_total_pct",
        "measurement_efficiency",
        "measurement_coverage_pct_x",

        # GM 0–5
        "stunting_total_pct_0_5",
        "underweight_total_pct_0_5",
        "measurement_coverage_pct_0_5",

        # Supporting Indicators
        "lbw_rate_pct",
        "pw_anaemia_rate",
        "ag_anaemia_rate",
        "optimum_wg_latest_pct",
        "visit_coverage_pct",
        "active_awc_pct",
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

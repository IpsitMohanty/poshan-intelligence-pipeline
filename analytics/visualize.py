# analytics/visualize.py

import pandas as pd
import matplotlib.pyplot as plt
import os

# Use non-interactive backend
plt.switch_backend("Agg")

# -------------------------------------------------------------------
#  CREATE FIXED OUTPUT FOLDER FOR PLOTS
# -------------------------------------------------------------------
PLOT_DIR = os.path.join(os.getcwd(), "plots")
os.makedirs(PLOT_DIR, exist_ok=True)
print(f"[DEBUG] Plots will be saved to: {PLOT_DIR}")


def load_cube(path: str) -> pd.DataFrame:
    """Load the district intelligence cube."""
    print(f"[DEBUG] Loading cube from: {path}")
    return pd.read_csv(path)


# ------------------------------------------------------------
# 1️⃣ TOP/BOTTOM BAR CHART
# ------------------------------------------------------------
def plot_top_bottom_bar(df: pd.DataFrame, column: str, n: int = 5):

    if column not in df.columns:
        print(f"[ERROR] Column '{column}' not found, skipping top/bottom…")
        return

    df_plot = df[["District", column]].dropna()

    top = df_plot.nlargest(n, column)
    bottom = df_plot.nsmallest(n, column)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    axes[0].barh(top["District"], top[column])
    axes[0].set_title(f"Top {n} districts – {column}")
    axes[0].invert_yaxis()

    axes[1].barh(bottom["District"], bottom[column])
    axes[1].set_title(f"Bottom {n} districts – {column}")
    axes[1].invert_yaxis()

    plt.tight_layout()

    filename = f"top_bottom_{column.replace('%','pct')}.png"
    file_path = os.path.join(PLOT_DIR, filename)
    plt.savefig(file_path, dpi=240, bbox_inches="tight")
    plt.close()

    print(f"[SAVED] {file_path}")


# ------------------------------------------------------------
# 2️⃣ SCATTER PLOT
# ------------------------------------------------------------
def plot_scatter(df: pd.DataFrame, x_col: str, y_col: str):

    for col in [x_col, y_col]:
        if col not in df.columns:
            print(f"[ERROR] Missing column '{col}', skipping scatter plot…")
            return

    df_plot = df[[x_col, y_col, "District"]].dropna()

    plt.figure(figsize=(7, 7))
    plt.scatter(df_plot[x_col], df_plot[y_col])

    # label each point
    for _, row in df_plot.iterrows():
        plt.text(row[x_col], row[y_col], row["District"], fontsize=6)

    plt.xlabel(x_col)
    plt.ylabel(y_col)
    plt.title(f"{y_col} vs {x_col}")
    plt.tight_layout()

    filename = f"scatter_{x_col}_vs_{y_col}.png"
    file_path = os.path.join(PLOT_DIR, filename)
    plt.savefig(file_path, dpi=240, bbox_inches="tight")
    plt.close()

    print(f"[SAVED] {file_path}")


# ------------------------------------------------------------
# 3️⃣ CORRELATION HEATMAP
# ------------------------------------------------------------
def plot_corr_heatmap(df: pd.DataFrame, columns: list):

    existing = [c for c in columns if c in df.columns]

    if len(existing) < 2:
        print("[ERROR] Not enough columns for correlation heatmap, skipping.")
        return

    corr = df[existing].corr()

    plt.figure(figsize=(10, 8))
    plt.imshow(corr, cmap="coolwarm", interpolation="nearest")
    plt.colorbar()

    plt.xticks(range(len(existing)), existing, rotation=45, ha="right")
    plt.yticks(range(len(existing)), existing)
    plt.title("Correlation Heatmap")
    plt.tight_layout()

    file_path = os.path.join(PLOT_DIR, "correlation_heatmap.png")
    plt.savefig(file_path, dpi=240, bbox_inches="tight")
    plt.close()

    print(f"[SAVED] {file_path}")


# ------------------------------------------------------------
# 4️⃣ BI SUBSET EXPORT
# ------------------------------------------------------------
def export_bi_subset(df: pd.DataFrame, out_path: str):

    print(f"[DEBUG] Exporting BI subset → {out_path}")

    cols = [
        "District",

        # GM 5–6
        "Stunting_Total_%",
        "Underweight_Total_%",
        "Measurement_Efficiency",
        "Measurement_Coverage_%",

        # GM 0–5
        "Stunting_Total_Pct_0_5",
        "Underweight_Total_Pct_0_5",
        "Measurement_Coverage_Pct_0_5",

        # Anaemia → LBW → AG
        "LBW_Rate_%",
        "PW_Anaemia_Rate",
        "AG_Anaemia_%",
        "Optimum_WG_Latest_%",

        # Service Delivery
        "HV_Percentage",
        "Active_AWC_%",

        # Severe Cases
        "SAM_Rate_%",
        "SUW_Rate_%"
    ]

    existing = [c for c in cols if c in df.columns]

    df[existing].to_csv(out_path, index=False)

    print(f"[SAVED] BI file at: {out_path}")

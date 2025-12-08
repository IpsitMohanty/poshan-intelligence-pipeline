from etl.loader import load_file
import pandas as pd

def analyze_gwg(path: str) -> pd.DataFrame:
    """Analyze Gestational Weight Gain (GWG) and ANC completeness."""

    print("\n=== Gestational Weight Gain (GWG) Analysis ===")

    df = load_file(path)

    # Standardize column names
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(" ", "_")
                  .str.replace(".", "")
                  .str.replace("__", "_")
    )

    # Rename columns to predictable internal names
    df = df.rename(columns={
        "district": "district",

        "total_active_pregnant_women": "total_pw",

        "no_of_pw_due_anc_1": "pw_due_anc1",
        "no_of_pw_completed_anc_1": "pw_completed_anc1",

        "no_of_pw_due_anc_2": "pw_due_anc2",
        "no_of_pw_completed_anc_2": "pw_completed_anc2",

        "no_of_pw_gained_optimum_weight_in_anc_2": "pw_optimum_anc2",

        "no_of_pw_due_anc_3": "pw_due_anc3",
        "no_of_pw_completed_anc_3": "pw_completed_anc3",
        "no_of_pw_gained_optimum_weight_in_anc_3": "pw_optimum_anc3",

        "no_of_pw_due_anc_4": "pw_due_anc4",
        "no_of_pw_completed_anc_4": "pw_completed_anc4",
        "no_of_pw_gained_optimum_weight_in_anc_4": "pw_optimum_anc4",

        "total_no_of_pw_gained_optimum_weight_as_per_latest_anc": "pw_optimum_latest",

        "total_haemoglobin_measured_as_per_latest_anc": "pw_hb_measured",
        "total_anaemic_as_per_latest_anc": "pw_anaemic_latest",
    })

    # -------------------------------
    # ANC COMPLETION RATES
    # -------------------------------
    def pct(num, den):
        return (num / den.replace(0, pd.NA)).astype(float).fillna(0).round(2)

    df["anc1_completion_pct"] = pct(df["pw_completed_anc1"], df["pw_due_anc1"])
    df["anc2_completion_pct"] = pct(df["pw_completed_anc2"], df["pw_due_anc2"])
    df["anc3_completion_pct"] = pct(df["pw_completed_anc3"], df["pw_due_anc3"])
    df["anc4_completion_pct"] = pct(df["pw_completed_anc4"], df["pw_due_anc4"])

    # -------------------------------
    # OPTIMUM WEIGHT GAIN
    # -------------------------------
    df["optimum_wg_latest_pct"] = pct(df["pw_optimum_latest"], df["total_pw"])

    # -------------------------------
    # HB MEASUREMENT RATE
    # -------------------------------
    df["pw_hb_measured_pct"] = pct(df["pw_hb_measured"], df["total_pw"])

    # -------------------------------
    # ANAEMIA RATE (Latest ANC)
    # -------------------------------
    df["pw_anaemia_latest_pct"] = pct(df["pw_anaemic_latest"], df["pw_hb_measured"])

    # -------------------------------
    # Clean district names
    # -------------------------------
    df["district"] = df["district"].astype(str).str.strip().str.title()

    return df

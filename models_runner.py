# models_runner.py
"""
Run predictive models using district_cube_*.csv
Cube file exists in the project root (not in /cubes/).
"""

import pandas as pd
import joblib
from pathlib import Path
from datetime import datetime

from analytics.models import predict_lbw, predict_stunting


# ---------------------------------------------------------
# Load cube from ROOT folder (because cube is in root)
# ---------------------------------------------------------
def load_latest_cube():
    """
    Loads district_cube_*.csv from project ROOT.
    Example: district_cube_2025_11.csv
    """
    root_path = Path(".")
    cube_files = sorted(root_path.glob("district_cube_*.csv"))

    if not cube_files:
        raise FileNotFoundError("❌ No district_cube_*.csv found in project root.")

    latest = cube_files[-1]
    print(f"\n📌 Loading cube: {latest.name}")

    df = pd.read_csv(latest)
    print(f"   → Loaded {df.shape[0]} rows, {df.shape[1]} columns")

    return df, latest.name


# ---------------------------------------------------------
# Save model
# ---------------------------------------------------------
def save_model(model, name: str):
    models_path = Path("models")
    models_path.mkdir(exist_ok=True)

    save_path = models_path / f"{name}.joblib"
    joblib.dump(model, save_path)
    print(f"   ✔ Model saved: {save_path}")


# ---------------------------------------------------------
# Save predictions to /cubes
# ---------------------------------------------------------
def save_predictions(df: pd.DataFrame, cube_name: str):
    Path("cubes").mkdir(exist_ok=True)  # ensure folder exists

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_name = f"predictions_{cube_name.replace('.csv','')}_{timestamp}.csv"
    output_path = Path("cubes") / output_name

    df.to_csv(output_path, index=False)
    print(f"\n📁 Predictions saved: {output_path}")


# ---------------------------------------------------------
# Runner
# ---------------------------------------------------------
def run_all_models():
    print("\n======================================")
    print("      RUNNING PREDICTIVE MODELS")
    print("======================================\n")

    df, cube_name = load_latest_cube()

    # --- LBW Model --------------------------------------------------
    print("\n🚀 Training LBW Model...")
    lbw_model, X_lbw, y_lbw = predict_lbw(df)
    save_model(lbw_model, "lbw_model")
    df["LBW_Predicted"] = lbw_model.predict(X_lbw)

    # --- Stunting Model ---------------------------------------------
    print("\n🚀 Training Stunting Model...")
    stunting_model, X_st, y_st = predict_stunting(df)
    save_model(stunting_model, "stunting_model")
    df["Stunting_Predicted"] = stunting_model.predict(X_st)

    # --- Save predictions -------------------------------------------
    save_predictions(df, cube_name)

    print("\n======================================")
    print("   ✔ ALL MODELS TRAINED SUCCESSFULLY")
    print("======================================\n")

    return df


if __name__ == "__main__":
    run_all_models()

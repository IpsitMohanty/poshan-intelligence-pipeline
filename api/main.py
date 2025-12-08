# api/main.py

from fastapi import FastAPI, HTTPException
import joblib
import pandas as pd
from pathlib import Path

from api.schemas import PredictRequest

app = FastAPI(
    title="Poshan Intelligence ML API",
    description="Predict LBW & Stunting using trained models",
    version="1.0"
)

# Load models
LBW_MODEL_PATH = Path("models/lbw_model.joblib")
STUNTING_MODEL_PATH = Path("models/stunting_model.joblib")

if not LBW_MODEL_PATH.exists() or not STUNTING_MODEL_PATH.exists():
    raise RuntimeError("❌ Trained models not found. Run models_runner.py first.")

lbw_model = joblib.load(LBW_MODEL_PATH)
stunting_model = joblib.load(STUNTING_MODEL_PATH)

# Load cube (for district insights)
cube_files = sorted(Path(".").glob("district_cube_*.csv"))
cube = pd.read_csv(cube_files[-1]) if cube_files else None


@app.get("/")
def root():
    return {"message": "Poshan Intelligence ML API is running!"}


# ---------------------------------------------------------
# Helper: Map request → model feature names
# ---------------------------------------------------------
LBW_MAPPING = {
    "PW_Anaemia_Rate": "PW_Anaemia_Rate",
    "Optimum_WG_Latest_": "Optimum_WG_Latest_%",
    "PW_Hb_Measured_": "PW_Hb_Measured_%",
    "Measurement_Efficiency": "Measurement_Efficiency",
    "HV_Percentage": "HV_Percentage",
    "SAM_Rate_": "SAM_Rate_%",
    "SUW_Rate_": "SUW_Rate_%"
}

LBW_FEATURE_ORDER = [
    "PW_Anaemia_Rate",
    "Optimum_WG_Latest_%",
    "PW_Hb_Measured_%",
    "Measurement_Efficiency",
    "HV_Percentage",
    "SAM_Rate_%",
    "SUW_Rate_%"
]


STUNTING_MAPPING = {
    "Measurement_Efficiency": "Measurement_Efficiency",
    "SAM_Rate_": "SAM_Rate_%",
    "SUW_Rate_": "SUW_Rate_%",
    "Active_AWC_": "Active_AWC_%",
    "HV_Percentage": "HV_Percentage",
    "LBW_Rate_": "LBW_Rate_%"
}

STUNTING_FEATURE_ORDER = [
    "Measurement_Efficiency",
    "SAM_Rate_%",
    "SUW_Rate_%",
    "Active_AWC_%",
    "HV_Percentage",
    "LBW_Rate_%"
]


# ---------------------------------------------------------
# Predict LBW
# ---------------------------------------------------------
@app.post("/predict/lbw")
def predict_lbw(req: PredictRequest):

    req_dict = req.dict()

    # Convert request → proper model feature names
    model_input = {}
    for req_key, value in req_dict.items():
        if value is not None and req_key in LBW_MAPPING:
            model_feature = LBW_MAPPING[req_key]
            model_input[model_feature] = value

    if not model_input:
        raise HTTPException(400, "No valid LBW features provided.")

    # Build input row in correct model training order
    input_row = {col: model_input.get(col, 0) for col in LBW_FEATURE_ORDER}

    df = pd.DataFrame([input_row])
    y_pred = lbw_model.predict(df)[0]

    return {
        "LBW_Predicted": round(float(y_pred), 2),
        "features_used": [k for k, v in input_row.items() if v != 0]
    }


# ---------------------------------------------------------
# Predict Stunting (Corrected Mapping Version)
# ---------------------------------------------------------
@app.post("/predict/stunting")
def predict_stunting(req: PredictRequest):

    req_dict = req.dict()

    # Request → Cube column mapping
    mapping = {
        "Measurement_Efficiency": "Measurement_Efficiency",
        "SAM_Rate_": "SAM_Rate_%",
        "SUW_Rate_": "SUW_Rate_%",
        "Active_AWC_": "Active_AWC_%",
        "HV_Percentage": "HV_Percentage",
        "LBW_Rate_": "LBW_Rate_%"
    }

    # Model’s expected feature order (MUST MATCH training)
    feature_order = [
        "Measurement_Efficiency",
        "SAM_Rate_%",
        "SUW_Rate_%",
        "Active_AWC_%",
        "HV_Percentage",
        "LBW_Rate_%"
    ]

    # Map request → proper model features
    model_input = {}
    for req_key, req_value in req_dict.items():
        if req_value is not None and req_key in mapping:
            model_feature = mapping[req_key]
            model_input[model_feature] = req_value

    if not model_input:
        raise HTTPException(400, "No valid features provided for Stunting prediction.")

    # Build row in correct training order
    input_row = {
        col: model_input.get(col, 0)  # missing features become 0
        for col in feature_order
    }

    df = pd.DataFrame([input_row])
    y_pred = stunting_model.predict(df)[0]

    return {
        "Stunting_Predicted": round(float(y_pred), 2),
        "features_used": [key for key, value in input_row.items() if value != 0]
    }


@app.get("/district/{name}")
def district_insights(name: str):
    if cube is None:
        raise HTTPException(500, "Cube not loaded.")

    name_clean = name.strip().lower()

    if "District" not in cube.columns:
        raise HTTPException(500, "District column not found in cube.")

    normalized = cube["District"].astype(str).str.strip().str.lower()

    matches = cube[normalized == name_clean]

    if matches.empty:
        matches = cube[normalized.str.contains(name_clean, na=False)]

    if matches.empty:
        available = sorted(cube["District"].dropna().unique())
        raise HTTPException(
            404,
            f"District '{name}' not found. Available districts: {', '.join(available)}"
        )

    row = matches.iloc[0].to_dict()

    # ⭐ FIX: Convert all values into JSON-safe types
    clean_row = {}
    for key, value in row.items():
        if pd.isna(value):
            clean_row[key] = None
        elif hasattr(value, "item"):  # numpy types
            clean_row[key] = value.item()
        else:
            clean_row[key] = value

    return clean_row
# ---------------------------------------------------------
# NEW: Structured District Insights (Includes 0–5 Data)
# ---------------------------------------------------------
@app.get("/district_structured/{name}")
def district_structured(name: str):
    if cube is None:
        raise HTTPException(500, "Cube not loaded.")

    # Normalize input name
    name_clean = name.strip().lower()
    normalized = cube["District"].astype(str).str.strip().str.lower()

    # Exact match
    matches = cube[normalized == name_clean]

    # Partial match fallback
    if matches.empty:
        matches = cube[normalized.str.contains(name_clean, na=False)]

    if matches.empty:
        available = sorted(cube["District"].dropna().unique())
        raise HTTPException(
            404,
            f"District '{name}' not found. Available districts: {', '.join(available)}"
        )

    row = matches.iloc[0].to_dict()

    # JSON-safe type conversion
    clean_row = {
        k: (None if pd.isna(v) else (v.item() if hasattr(v, "item") else v))
        for k, v in row.items()
    }

    # ---------------------------
    # STRUCTURED OUTPUT FORMAT
    # ---------------------------
    response = {
        "district": clean_row.get("District"),

        "stunting_5_6": {
            "stunting_pct": clean_row.get("Stunting_Total_%"),
            "underweight_pct": clean_row.get("Underweight_Total_%"),
            "measurement_efficiency": clean_row.get("Measurement_Efficiency"),
        },

        "stunting_0_5": {
            "stunting_pct": clean_row.get("Stunting_Total_Pct_0_5"),
            "underweight_pct": clean_row.get("Underweight_Total_Pct_0_5"),
            "measurement_coverage": clean_row.get("Measurement_Coverage_Pct_0_5"),
        },

        "maternal_indicators": {
            "pw_anaemia_rate": clean_row.get("PW_Anaemia_Rate"),
            "optimum_weight_gain": clean_row.get("Optimum_WG_Latest_%"),
        },

        "service_delivery": {
            "home_visit_pct": clean_row.get("HV_Percentage"),
            "active_awc_pct": clean_row.get("Active_AWC_%"),
        },

        "raw": clean_row  # returns all 150+ fields
    }

    return response



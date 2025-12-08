# analytics/models.py

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error

def _train_model(df: pd.DataFrame, feature_cols: list, target_col: str):
    data = df.dropna(subset=feature_cols + [target_col]).copy()
    X = data[feature_cols]
    y = data[target_col]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=200,
        random_state=42
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print(f"\n=== Model for {target_col} ===")
    print(f"R²: {r2_score(y_test, y_pred):.3f}")
    print(f"MAE: {mean_absolute_error(y_test, y_pred):.3f}")

    # Feature importance
    fi = sorted(
        zip(feature_cols, model.feature_importances_),
        key=lambda x: x[1],
        reverse=True
    )
    print("Feature importance:")
    for name, score in fi:
        print(f"  {name}: {score:.3f}")

    return model, X, y


def predict_lbw(df: pd.DataFrame):
    """
    Predict LBW_Rate_% using maternal & service indicators.
    Adjust feature list based on actual cube columns.
    """
    features = [
        "PW_Anaemia_Rate",
        "Optimum_WG_Latest_%",
        "PW_Hb_Measured_%",
        "Measurement_Efficiency",
        "HV_Percentage",
        "SAM_Rate_%",
        "SUW_Rate_%",
    ]
    features = [c for c in features if c in df.columns]
    return _train_model(df, features, "LBW_Rate_%")

def predict_stunting(df: pd.DataFrame):
    """
    Predict Stunting_Total_% from SNP, ME, AWC, etc.
    """
    features = [
        "Measurement_Efficiency",
        "SAM_Rate_%",
        "SUW_Rate_%",
        "Active_AWC_%",
        "HV_Percentage",
        "LBW_Rate_%",
    ]
    features = [c for c in features if c in df.columns]
    return _train_model(df, features, "Stunting_Total_%")

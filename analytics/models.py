# analytics/models.py

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error

MIN_TRAINING_ROWS = 10


def _train_model(df: pd.DataFrame, feature_cols: list, target_col: str):
    data = df.dropna(subset=feature_cols + [target_col]).copy()
    if len(data) < MIN_TRAINING_ROWS:
        raise ValueError(
            f"Insufficient data to train model for {target_col}: "
            f"need at least {MIN_TRAINING_ROWS} rows, got {len(data)}."
        )
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
    Predict lbw_rate_pct using maternal & service indicators.
    Adjust feature list based on actual cube columns.
    """
    features = [
        "pw_anaemia_rate",
        "optimum_wg_latest_pct",
        "pw_hb_measured_pct",
        "measurement_efficiency",
        "visit_coverage_pct",
        "sam_ratio",
        "suw_ratio",
    ]
    features = [c for c in features if c in df.columns]
    return _train_model(df, features, "lbw_rate_pct")

def predict_stunting(df: pd.DataFrame):
    """
    Predict stunting_total_pct from SNP, ME, AWC, etc.
    """
    features = [
        "measurement_efficiency",
        "sam_ratio",
        "suw_ratio",
        "active_awc_pct",
        "visit_coverage_pct",
        "lbw_rate_pct",
    ]
    features = [c for c in features if c in df.columns]
    return _train_model(df, features, "stunting_total_pct")

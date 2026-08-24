import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestRegressor
from analytics.models import predict_lbw, predict_stunting


def _make_cube(n=60, seed=42):
    # Column names match the real build_district_cube() schema
    # (lowercase_snake_case throughout - see cubes/district_cube.py's
    # standardize_columns) - not the pre-refactor Title_Case names.
    # tests/test_models_integration.py exercises the real cube directly so
    # this fixture's naming can't silently drift from it again.
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "district": [f"District_{i}" for i in range(n)],
        "pw_anaemia_rate": rng.uniform(20, 60, n),
        "optimum_wg_latest_pct": rng.uniform(30, 70, n),
        "pw_hb_measured_pct": rng.uniform(40, 90, n),
        "measurement_efficiency": rng.uniform(50, 95, n),
        "visit_coverage_pct": rng.uniform(40, 80, n),
        "sam_ratio": rng.uniform(1, 8, n),
        "suw_ratio": rng.uniform(5, 25, n),
        "active_awc_pct": rng.uniform(70, 100, n),
        "lbw_rate_pct": rng.uniform(5, 20, n),
        "stunting_total_pct": rng.uniform(20, 50, n),
    })


class TestPredictLbw:
    def test_returns_model_and_data(self):
        df = _make_cube()
        model, X, y = predict_lbw(df)
        assert model is not None
        assert isinstance(model, RandomForestRegressor)
        assert len(X) == len(y)

    def test_model_can_predict(self):
        df = _make_cube()
        model, X, _ = predict_lbw(df)
        preds = model.predict(X.iloc[:5])
        assert len(preds) == 5
        assert all(np.isfinite(p) for p in preds)

    def test_ignores_missing_feature_columns(self):
        df = _make_cube().drop(columns=["optimum_wg_latest_pct", "pw_hb_measured_pct"])
        # Should still train on the available features without raising
        model, X, _ = predict_lbw(df)
        assert model is not None

    def test_raises_on_insufficient_data(self):
        df = _make_cube(n=2)
        with pytest.raises(Exception):
            predict_lbw(df)


class TestPredictStunting:
    def test_returns_model_and_data(self):
        df = _make_cube()
        model, X, y = predict_stunting(df)
        assert model is not None
        assert isinstance(model, RandomForestRegressor)

    def test_model_can_predict(self):
        df = _make_cube()
        model, X, _ = predict_stunting(df)
        preds = model.predict(X.iloc[:5])
        assert len(preds) == 5
        assert all(np.isfinite(p) for p in preds)

    def test_feature_importances_sum_to_one(self):
        df = _make_cube()
        model, _, _ = predict_stunting(df)
        assert sum(model.feature_importances_) == pytest.approx(1.0, abs=1e-6)

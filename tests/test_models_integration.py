"""Coverage: the seam between cubes/district_cube.py's real output and
analytics/models.py's predict_lbw/predict_stunting.

This is the seam that broke silently for a while: build_district_cube()
uses lowercase_snake_case columns (cubes/district_cube.py's
standardize_columns), but analytics/models.py, visuals.py, correlate.py,
and main.py were still written against an older Title_Case_With_%
schema. tests/test_models.py's own fixture used that same stale naming,
so nothing caught the mismatch - predict_stunting(build_district_cube(...))
raised KeyError on "Stunting_Total_%" against real data, every time,
undetected by the 78-test suite. Fixed alongside this test; this test
pins the fix by running predict_lbw/predict_stunting against the actual
cube-building code path instead of an independently-named fixture, so a
future rename on one side without the other fails here immediately.

Uses whatever is currently in data/2025-11 (real data pre-Phase 2,
synthetic data after it) - the point is exercising the real column names
build_district_cube() actually produces, not any particular month's
values.
"""
import pytest
from sklearn.ensemble import RandomForestRegressor

from cubes.district_cube import build_district_cube
from analytics.models import predict_lbw, predict_stunting

DATA_DIR = "data/2025-11"


@pytest.fixture(scope="module")
def cube():
    return build_district_cube(DATA_DIR)


def test_cube_has_the_columns_predict_lbw_and_predict_stunting_expect(cube):
    # Both targets must exist verbatim - _train_model does not fall back
    # or filter the target column the way it filters features.
    assert "lbw_rate_pct" in cube.columns
    assert "stunting_total_pct" in cube.columns


def test_predict_lbw_runs_against_the_real_cube(cube):
    model, X, y = predict_lbw(cube)
    assert isinstance(model, RandomForestRegressor)
    assert len(X) == len(y)
    preds = model.predict(X.iloc[:5])
    assert len(preds) == 5


def test_predict_stunting_runs_against_the_real_cube(cube):
    model, X, y = predict_stunting(cube)
    assert isinstance(model, RandomForestRegressor)
    assert len(X) == len(y)
    preds = model.predict(X.iloc[:5])
    assert len(preds) == 5

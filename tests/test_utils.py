import pandas as pd
import pytest
from utils.cleaner import standardize_columns, normalize_awc_code, fill_missing
from utils.stats import safe_corr, top_bottom


class TestStandardizeColumns:
    def test_strips_whitespace(self):
        df = pd.DataFrame([[1]], columns=[" Total Count "])
        result = standardize_columns(df)
        assert "total_count" in result.columns

    def test_replaces_spaces_with_underscores(self):
        df = pd.DataFrame([[1]], columns=["District Name"])
        result = standardize_columns(df)
        assert "district_name" in result.columns

    def test_removes_special_chars(self):
        df = pd.DataFrame([[1]], columns=["Rate (%)"])
        result = standardize_columns(df)
        assert any("rate" in c for c in result.columns)

    def test_lowercases(self):
        df = pd.DataFrame([[1]], columns=["AWC_CODE"])
        result = standardize_columns(df)
        assert "awc_code" in result.columns


class TestNormalizeAwcCode:
    def test_pads_to_11_digits(self):
        df = pd.DataFrame({"awc_code": ["123", "45678"]})
        result = normalize_awc_code(df)
        assert result["awc_code"].iloc[0] == "00000000123"
        assert result["awc_code"].iloc[1] == "00000045678"

    def test_already_11_digits_unchanged(self):
        df = pd.DataFrame({"awc_code": ["21398130220"]})
        result = normalize_awc_code(df)
        assert result["awc_code"].iloc[0] == "21398130220"


class TestFillMissing:
    def test_zero_strategy(self):
        df = pd.DataFrame({"a": [1.0, None, 3.0]})
        result = fill_missing(df, strategy="zero")
        assert result["a"].iloc[1] == 0.0

    def test_ffill_strategy(self):
        df = pd.DataFrame({"a": [1.0, None, None]})
        result = fill_missing(df, strategy="ffill")
        assert result["a"].iloc[1] == 1.0
        assert result["a"].iloc[2] == 1.0

    def test_unknown_strategy_returns_unchanged(self):
        df = pd.DataFrame({"a": [1.0, None]})
        result = fill_missing(df, strategy="unknown")
        assert result["a"].isna().any()


class TestSafeCorr:
    def test_returns_square_matrix(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": [3, 2, 1]})
        result = safe_corr(df)
        assert result.shape == (2, 2)

    def test_diagonal_is_one(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        result = safe_corr(df)
        assert result.loc["x", "x"] == pytest.approx(1.0)

    def test_negative_correlation(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": [3, 2, 1]})
        result = safe_corr(df)
        assert result.loc["x", "y"] == pytest.approx(-1.0)


class TestTopBottom:
    def test_returns_top_n(self):
        df = pd.DataFrame({"val": range(20)})
        top, _ = top_bottom(df, "val", n=5)
        assert len(top) == 5
        assert top["val"].min() == 15

    def test_returns_bottom_n(self):
        df = pd.DataFrame({"val": range(20)})
        _, bottom = top_bottom(df, "val", n=5)
        assert len(bottom) == 5
        assert bottom["val"].max() == 4

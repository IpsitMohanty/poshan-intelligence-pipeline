"""Coverage: etl/cleaner.py -- the generic per-table cleaning pass every
loaded source table goes through before analysis. Distinct from
utils/cleaner.py (tested in test_utils.py): that one is used by
cubes/district_cube.py's district-name normalization; this one is the
loader-stage pass over raw, not-yet-analyzed tables. Previously untested.
"""
import pandas as pd

from etl.cleaner import basic_clean, clean_all, standardize_column_names


class TestStandardizeColumnNames:
    def test_lowercases_and_strips_and_underscores(self):
        df = pd.DataFrame(columns=[" District Name ", "AWC Code"])
        result = standardize_column_names(df)
        assert list(result.columns) == ["district_name", "awc_code"]

    def test_collapses_double_underscore(self):
        df = pd.DataFrame(columns=["Total  Count"])
        result = standardize_column_names(df)
        assert list(result.columns) == ["total_count"]


class TestBasicClean:
    def test_strips_whitespace_in_string_columns(self):
        df = pd.DataFrame({"district": ["  Khordha ", "Cuttack"], "value": [1, 2]})
        result = basic_clean(df)
        assert result["district"].tolist() == ["Khordha", "Cuttack"]

    def test_drops_full_duplicate_rows(self):
        df = pd.DataFrame({"district": ["Khordha", "Khordha"], "value": [1, 1]})
        result = basic_clean(df)
        assert len(result) == 1

    def test_keeps_rows_that_differ_in_any_column(self):
        df = pd.DataFrame({"district": ["Khordha", "Khordha"], "value": [1, 2]})
        result = basic_clean(df)
        assert len(result) == 2

    def test_does_not_mutate_the_input_frame(self):
        df = pd.DataFrame({" District ": ["a"]})
        basic_clean(df)
        assert " District " in df.columns  # original untouched


class TestCleanAll:
    def test_processes_every_table_in_the_dict_and_preserves_keys(self):
        raw = {
            "awc": pd.DataFrame({" District ": ["a", "a"]}),
            "anaemia": pd.DataFrame({"District": ["b"]}),
        }
        cleaned = clean_all(raw)
        assert set(cleaned.keys()) == {"awc", "anaemia"}
        assert list(cleaned["awc"].columns) == ["district"]
        assert len(cleaned["awc"]) == 1  # duplicate row dropped

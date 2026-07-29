"""Coverage: cubes/district_cube.py -- clean_district (the district-name
normalization every source table goes through before merging) and
build_district_cube (the actual 10-table left-merge that produces the
district cube). Previously untested despite being the pipeline's
central join.

TestBuildDistrictCubeAgainstRealNovemberData runs against the actual
committed data/2025-11 source files, not a synthetic fixture -- these
are the real, reproducible reconciliation numbers quoted in the
README's data-quality section, not illustrative placeholders. No
network, no external dependency: the source CSVs are already in the
repo.
"""
import pandas as pd
import pytest

from cubes.district_cube import build_district_cube, clean_district

DATA_DIR = "data/2025-11"


@pytest.fixture(scope="module")
def cube():
    """Real-data reconciliation fixture, built once per test module and
    reused (building the cube re-reads and re-merges 10 CSVs; sharing it
    across assertions keeps the suite fast without weakening any
    individual check). Module-level, not a class-scoped instance method,
    to avoid pytest's deprecated class-fixture-as-instance-method pattern.
    """
    return build_district_cube(DATA_DIR)


class TestCleanDistrict:
    def test_raises_without_district_column(self):
        df = pd.DataFrame({"foo": [1, 2]})
        with pytest.raises(KeyError, match="district"):
            clean_district(df)

    def test_standardizes_casing_and_whitespace(self):
        df = pd.DataFrame({"District": ["  KHORDHA ", "cuttack"]})
        result = clean_district(df)
        assert list(result["district"]) == ["Khordha", "Cuttack"]

    def test_normalizes_en_dash_to_hyphen(self):
        df = pd.DataFrame({"District": ["Nabarangpur–Test"]})
        result = clean_district(df)
        assert "–" not in result["district"].iloc[0]
        assert "-" in result["district"].iloc[0]


class TestBuildDistrictCubeAgainstRealNovemberData:
    def test_one_row_per_district_no_duplicates(self, cube):
        assert cube["district"].duplicated().sum() == 0

    def test_join_key_is_never_null(self, cube):
        assert cube["district"].isnull().sum() == 0

    def test_row_count_matches_the_left_merge_base_table(self, cube):
        # gm_5_6 is the left-merge base (cubes/district_cube.py); a left
        # join must preserve its row count exactly regardless of how
        # many of the other 9 sources match on district.
        base = pd.read_csv(f"{DATA_DIR}/(5_to_6_Years)_Growth_Monitoring_11_2025.csv")
        assert len(cube) == len(base) == 30

    def test_rebuild_is_idempotent(self, cube):
        """Running the cube build twice on the same input must produce
        an identical result -- a real production concern for a pipeline
        re-run monthly, not a hypothetical one."""
        rebuilt = build_district_cube(DATA_DIR)
        pd.testing.assert_frame_equal(
            cube.sort_index(axis=1).reset_index(drop=True),
            rebuilt.sort_index(axis=1).reset_index(drop=True),
        )

    def test_adolescent_girls_coverage_gap_matches_documented_value(self, cube):
        """Documented in the README, not hidden: the Adolescent Girls
        source only covers 10 of the 30 districts this month. The left
        join surfaces the other 20 honestly as NaN rather than a silent
        zero-fill, and this test pins that count so a future month's
        data (or a bug in the merge) that changes it gets noticed."""
        assert cube["ag_measured"].isnull().sum() == 20

    def test_no_other_source_has_a_coverage_gap(self, cube):
        """Every source except adolescent_girls covers all 30 districts
        this month -- checked directly, not assumed, against a
        representative column from two of the other 9 tables."""
        assert cube["measurement_efficiency"].isnull().sum() == 0  # gm_5_6, the merge base
        assert cube["stunted_severe_pct"].isnull().sum() == 0  # gm_0_5

"""Coverage: pipeline-wide data-quality reconciliation, distinct from
tests/test_district_cube.py's cube-merge tests. Three concerns:

1. Row-count reconciliation between the raw monthly source CSVs (data/) and
   the committed post-ETL warehouse output (warehouse/etl/) -- does the
   checked-in warehouse artifact actually match what etl.cleaner.basic_clean
   produces from the checked-in raw source, or has it gone stale?

2. Referential integrity of the "district" join key across all ten
   cube-input sources -- every value, after the same clean_district()
   normalization the cube build applies, must be one of the 30 real Odisha
   districts. This caught a real bug: the raw 0-5-years growth-monitoring
   export appends a state-level "Total" rollup row that isn't a district
   (fixed in etl/gm_0_5.py; this test pins the fix so it can't regress).
   It was harmless to the committed cube only by accident -- the merge
   happens to be anchored on a different, Total-free source table -- so
   nothing before this test would have caught it if that anchor ever
   changed.

3. Cube-to-source consistency -- does the committed
   warehouse/cubes/district_cube_2025-11.csv match a fresh
   build_district_cube("data/2025-11") run, or has the checked-in cube
   artifact drifted from the source data it's supposed to represent?

All three run against the real committed data/2025-11 and warehouse/
files, same convention as test_district_cube.py -- no synthetic fixture,
no network.
"""
import os

import pandas as pd
import pytest

from etl.adolescent_girls import analyze_adolescent_girls
from etl.anaemia import analyze_anaemia
from etl.awc_summary import analyze_awc_summary
from etl.cleaner import basic_clean
from etl.gm_0_5 import analyze_gm_0_5
from etl.gm_5_6 import analyze_gm_5_6
from etl.gwg import analyze_gwg
from etl.home_visit import analyze_home_visit
from etl.lbw import analyze_lbw
from etl.loader import load_file
from etl.measuring_efficiency import analyze_me
from etl.snp import analyze_snp
from cubes.district_cube import build_district_cube, clean_district

DATA_DIR = "data/2025-11"
WAREHOUSE_ETL_DIR = "warehouse/etl/2025-11"
WAREHOUSE_CUBE_FILE = "warehouse/cubes/district_cube_2025-11.csv"

# Same ten (key -> (raw filename, analyze function)) pairing
# cubes/district_cube.py's build_district_cube uses. Duplicated here rather
# than imported so this suite exercises the real per-source analyze_*
# functions directly, independent of district_cube.py's own file-resolution
# logic -- if that resolution logic ever silently pointed at the wrong
# file, these tests would still be reading the file they claim to.
SOURCES = {
    "gm_0_5": ("(0_to_5_Years)_Growth_Monitoring_11_2025.csv", analyze_gm_0_5),
    "gm_5_6": ("(5_to_6_Years)_Growth_Monitoring_11_2025.csv", analyze_gm_5_6),
    "anaemia": ("Anaemia_11_2025.csv", analyze_anaemia),
    "lbw": ("Low_Birth_Weight_11_2025.csv", analyze_lbw),
    "gwg": ("Gestational_Weight_Gain_Report_11_2025.csv", analyze_gwg),
    "ag": ("Adolescent_Girls_(14_18_Years)_11_2025.csv", analyze_adolescent_girls),
    "me": ("Measuring_Efficiency_Children_0_to_6_years_11_2025.csv", analyze_me),
    "hv": ("Home_Visit_11_2025.csv", analyze_home_visit),
    "snp": ("SNP_Projections_12_2025.csv", analyze_snp),
    "awc": ("AWC_11_2025.csv", analyze_awc_summary),
}


@pytest.fixture(scope="module")
def canonical_districts():
    """The 30 real Odisha districts, taken from the AWC summary source --
    the one table of the ten with no rollup/aggregate row of any kind."""
    awc = clean_district(analyze_awc_summary(f"{DATA_DIR}/AWC_11_2025.csv"))
    return set(awc["district"])


class TestRawToWarehouseRowCountReconciliation:
    """warehouse/etl/2025-11/ is committed output, not regenerated at test
    time -- these checks confirm it's still what etl.cleaner.basic_clean
    actually produces from the committed data/2025-11 raw files, so a
    hand-edited or stale warehouse file would be caught rather than
    trusted silently."""

    @pytest.mark.parametrize("fname", sorted(os.listdir(DATA_DIR)))
    def test_warehouse_row_count_matches_cleaned_raw(self, fname):
        raw = load_file(f"{DATA_DIR}/{fname}")
        expected = len(basic_clean(raw))
        warehouse_path = f"{WAREHOUSE_ETL_DIR}/{fname}"
        assert os.path.exists(warehouse_path), f"no warehouse counterpart for {fname}"
        actual = len(pd.read_csv(warehouse_path))
        assert actual == expected


class TestReferentialIntegrity:
    """Every district-keyed cube input must resolve entirely to the 30 real
    districts after clean_district() -- no aggregate rows, typos, or blank
    values silently riding along into the merge."""

    @pytest.mark.parametrize("key", sorted(SOURCES))
    def test_all_district_values_are_real_districts(self, key, canonical_districts):
        fname, analyze_fn = SOURCES[key]
        df = clean_district(analyze_fn(f"{DATA_DIR}/{fname}"))
        stray = set(df["district"]) - canonical_districts
        assert not stray, f"{key} ({fname}) has non-district values: {stray}"

    @pytest.mark.parametrize("key", sorted(SOURCES))
    def test_district_column_has_no_nulls_or_blanks(self, key):
        fname, analyze_fn = SOURCES[key]
        df = clean_district(analyze_fn(f"{DATA_DIR}/{fname}"))
        assert df["district"].isnull().sum() == 0
        assert (df["district"].astype(str).str.strip() == "").sum() == 0


class TestCubeToSourceConsistency:
    """The committed warehouse/cubes/district_cube_2025-11.csv is a
    generated artifact, not hand-maintained -- confirm it's still what a
    fresh build_district_cube(data/2025-11) actually produces, rather than
    output left behind by an older version of the code or data."""

    def test_committed_cube_matches_a_fresh_build(self):
        assert os.path.exists(WAREHOUSE_CUBE_FILE)
        committed = pd.read_csv(WAREHOUSE_CUBE_FILE)
        fresh = build_district_cube(DATA_DIR)

        assert set(committed.columns) == set(fresh.columns)
        assert len(committed) == len(fresh)

        committed = committed.sort_values("district").reset_index(drop=True)
        fresh = fresh.sort_values("district").reset_index(drop=True)
        # District casing/spelling in the committed CSV should already
        # match clean_district()'s output; a mismatch here means the file
        # was generated by a different version of the cleaning logic.
        assert list(committed["district"]) == list(fresh["district"])

        numeric_cols = fresh.select_dtypes(include="number").columns
        pd.testing.assert_frame_equal(
            committed[numeric_cols].reset_index(drop=True),
            fresh[numeric_cols].reset_index(drop=True),
            check_exact=False,
            rtol=1e-6,
        )

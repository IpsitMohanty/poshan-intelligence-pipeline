# Poshan Intelligence Pipeline

[![CI](https://github.com/IpsitMohanty/poshan-intelligence-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/IpsitMohanty/poshan-intelligence-pipeline/actions/workflows/ci.yml)

An ETL and analytics pipeline over monthly Anganwadi Centre (AWC) and Poshan reporting data: ten source-specific transformation modules feed a district-level cube, which in turn supports correlation analysis, lightweight predictive models, and a FastAPI serving layer.

This is the data-engineering piece of a broader set of projects built on the same public-sector Poshan/AWC domain -- a real, multi-stage warehouse pipeline (extract from monthly CSVs, clean and harmonize, build a reconciled district cube, model and serve), not a single notebook or one-off script.

## Problem

Monthly AWC reporting arrives as ten separately-formatted CSV exports (growth monitoring, anaemia, low birth weight, home visits, and so on), each with its own column naming and occasional gaps in district coverage. Turning that into one district-level analytical layer -- reliably, every month, without silently dropping or fabricating missing data -- is the actual engineering problem; the correlation analysis, prediction, and API layers downstream all depend on that layer being trustworthy.

## Approach

```
Monthly source CSVs -> ETL modules (per-source cleaning) -> district cube (left-merge on district) -> analytics / models / visuals -> API
```

- `etl/` -- one module per reporting stream (adolescent girls, anaemia, AWC summary, home visits, low birth weight, growth monitoring 0-5 and 5-6, gestational weight gain, measuring efficiency, SNP), each normalizing its own source's column names into a clean, district-keyed table.
- `cubes/district_cube.py` -- merges all ten cleaned tables into one district cube via a left join anchored on the growth-monitoring (5-6 years) table, so that table's row count and district coverage survives the merge regardless of what the other nine sources contain.
- `analytics/` -- correlation analysis and lightweight prediction (`predict_lbw`, `predict_stunting`) over the cube.
- `api/` -- FastAPI endpoints serving model predictions and district-level insight, with request/response schemas.
- `models/` -- serialized model artifacts from `models_runner.py`.

## Running it

Install dependencies:

```bash
pip install -r requirements.txt
```

Build the district cube:

```bash
python main.py
```

Run correlation analysis, generate visuals, or serve the API:

```bash
python correlate.py
python visuals.py
uvicorn api.main:app --reload
```

Containerized runs are available via `Dockerfile.api`, `Dockerfile.etl`, `Dockerfile.cube`, and `docker-compose.yml`.

## Tests

```bash
pip install -r requirements.txt pytest httpx
pytest -v
```

78 tests. Coverage spans:

- **`tests/test_utils.py`** -- pure utility functions (`standardize_columns`, `normalize_awc_code`, `fill_missing`, `safe_corr`, `top_bottom`).
- **`tests/test_etl_cleaner.py`** -- the generic loader-stage cleaning pass (`etl/cleaner.py`): column standardization, whitespace stripping, duplicate-row dropping, and that it doesn't mutate its input.
- **`tests/test_district_cube.py`** -- district-name normalization and the actual ten-table merge, checked against both a synthetic input and the real committed `data/2025-11` source files (see Results below).
- **`tests/test_pipeline_reconciliation.py`** -- pipeline-wide data-quality gates, run against the real committed `data/` and `warehouse/` files: raw-to-warehouse row-count reconciliation per source, referential integrity of the `district` join key against the 30 real Odisha districts for all ten cube-input sources individually, and consistency of the committed cube artifact against a fresh rebuild (see Results below).
- **`tests/test_models.py`** -- `predict_lbw` / `predict_stunting` return a fitted `RandomForestRegressor`, produce finite predictions, handle missing feature columns, and raise on insufficient data rather than silently misfitting.
- **`tests/test_api.py`** -- FastAPI endpoints via `TestClient`, with `joblib.load` / `pandas.read_csv` mocked so no model files are required to run the suite.

CI runs the suite (plus flake8, mypy, and a Docker build for each of the three images) on every push to `main`.

## Results: data-quality reconciliation

For an ETL/warehouse pipeline, "evaluation" means checking that the merge didn't silently lose or fabricate data -- not an ML metric. These numbers come from the real committed `data/2025-11` and `warehouse/` files (30 Odisha districts), not a synthetic example:

| check | result |
|---|---|
| Row count after merge | 30 -- matches the growth-monitoring (5-6 years) base table exactly, as a left join guarantees |
| Duplicate district keys | 0 |
| Null join keys | 0 |
| Rebuild determinism | Identical output across two runs on the same input, checked directly |
| Per-source district coverage | 9 of 10 sources cover all 30 districts this month |
| Raw-to-warehouse row counts | All 13 committed `data/2025-11` sources reconcile exactly against their `warehouse/etl/2025-11` counterpart (`tests/test_pipeline_reconciliation.py::TestRawToWarehouseRowCountReconciliation`) |
| Referential integrity of `district` | All ten cube-input sources resolve entirely to the 30 real districts after cleaning, individually checked (`TestReferentialIntegrity`) |
| Committed cube vs. fresh rebuild | `warehouse/cubes/district_cube_2025-11.csv` matches `build_district_cube("data/2025-11")` exactly, column-for-column and district-for-district (`TestCubeToSourceConsistency`) |

**The one real gap, reported rather than hidden**: the Adolescent Girls (14-18 years) source covers only 10 of the 30 districts this month -- the other 20 districts' `ag_*` columns are correctly `NaN` after the left join, not zero-filled or dropped. `tests/test_district_cube.py::test_adolescent_girls_coverage_gap_matches_documented_value` pins this exact count (20) so a future month's data, or a change to the merge logic, that alters it gets caught rather than silently drifting.

**A second gap the new referential-integrity pass found and fixed**: the raw `(0_to_5_Years)_Growth_Monitoring_11_2025.csv` export appends a state-level "Total" rollup row after the 30 districts. It wasn't affecting the committed cube -- the merge happens to be anchored on a different, Total-free source table -- but any source iterating that table's `district` values directly would have silently treated "Total" as a 31st district. Fixed in `etl/gm_0_5.py` (the row is now dropped before analysis); `TestReferentialIntegrity` pins the fix so it can't regress unnoticed again.

## Limitations

- Reconciliation was checked against one month of real data (November 2025), not a multi-month history -- month-to-month stability of these numbers (e.g. whether the Adolescent Girls gap recurs, worsens, or is specific to this month) isn't measured here.
- The Adolescent Girls coverage gap is reported, not root-caused: whether it reflects a genuine reporting gap at those 20 districts, a filename/format mismatch in the source export, or something else in the ten-source pipeline isn't investigated in this pass.
- Test coverage is real but uneven across the pipeline: the shared cleaning utilities, the district-cube merge, the prediction models, the API layer, and now each of the ten individual per-source `etl/` transformation modules' district-key output are all covered; the non-district-key columns those modules derive (e.g. the stunting/underweight ratios) are still only exercised indirectly through the cube-build integration test, not with dedicated per-column unit tests.
- `predict_lbw` / `predict_stunting` are lightweight `RandomForestRegressor` fits over the district cube, not tuned or validated against a held-out period -- the tests confirm the models fit and predict without crashing, not that their predictions are accurate.

## Container Setup

`Dockerfile.api`, `Dockerfile.etl`, `Dockerfile.cube`, and `docker-compose.yml` support containerized runs of each pipeline component; CI builds all three images on every push.

## Data Notes

The workflow expects monthly local source CSV files organized by month folders (`data/YYYY-MM/`) and produces cube/warehouse outputs keyed to that same month tag.

## Project Scope

ETL-driven Poshan analytics over public-scale AWC reporting data: district cube generation, correlation analysis, lightweight predictive modeling, and a FastAPI serving layer over the result.

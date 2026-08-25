# Poshan Intelligence Pipeline

[![CI](https://github.com/IpsitMohanty/poshan-intelligence-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/IpsitMohanty/poshan-intelligence-pipeline/actions/workflows/ci.yml)

An ETL and analytics pipeline over monthly Anganwadi Centre (AWC) and Poshan reporting data: ten source-specific transformation modules feed a district-level cube, which in turn supports correlation analysis, lightweight predictive models, and a FastAPI serving layer.

This is the data-engineering piece of a broader set of projects built on the same public-sector Poshan/AWC domain -- a real, multi-stage warehouse pipeline (extract from monthly CSVs, clean and harmonize, build a reconciled district cube, model and serve), not a single notebook or one-off script.

**Data provenance**: the committed `data/2025-11` and everything derived from it (`warehouse/`, the district cube, the trained models, the plots) are **seeded synthetic data**, not real government figures -- see [Synthetic Data Provenance](#synthetic-data-provenance) below for what's preserved, what isn't, and why.

## Problem

Monthly AWC reporting arrives as ten separately-formatted CSV exports (growth monitoring, anaemia, low birth weight, home visits, and so on), each with its own column naming and occasional gaps in district coverage. Turning that into one district-level analytical layer -- reliably, every month, without silently dropping or fabricating missing data -- is the actual engineering problem; the correlation analysis, prediction, and API layers downstream all depend on that layer being trustworthy.

## Approach

```
Monthly source CSVs -> ETL modules (per-source cleaning) -> district cube (left-merge on district) -> analytics / models / visuals -> API
```

- `etl/` -- one module per reporting stream (adolescent girls, anaemia, AWC summary, home visits, low birth weight, growth monitoring 0-5 and 5-6, gestational weight gain, measuring efficiency, SNP), each normalizing its own source's column names into a clean, district-keyed table. Ten modules for ten of the month's 13 real source files -- `AWC_Staff`, `VHSND_and_CBE`, and the Measurement Efficiency *Status* file (distinct from the Measuring Efficiency *Children* file the `me` module reads) go through the same generic loader/cleaner pass but don't get a dedicated module or feed the cube merge, which is why raw-to-warehouse reconciliation below counts 13 sources while the cube-input checks count ten.
- `cubes/district_cube.py` -- merges all ten cleaned tables into one district cube via a left join anchored on the growth-monitoring (5-6 years) table, so that table's row count and district coverage survives the merge regardless of what the other nine sources contain.
- `analytics/` -- correlation analysis over the cube, plus two `RandomForestRegressor` fits (`predict_lbw`, `predict_stunting`) kept in place and tested, but reported as findings rather than shipped predictors: LBW as a structured small-sample negative result, stunting as a leakage-checked correlation -- see [Model Layer Findings](#model-layer-findings).
- `api/` -- FastAPI endpoints serving model predictions and district-level insight, with request/response schemas.
- `models/` -- serialized model artifacts from `models_runner.py`.
- `dags/` -- the same chain expressed as an Airflow DAG, as an orchestration-tooling demonstration -- see [Airflow DAG](#airflow-dag-tooling-demonstration) below.

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

81 tests (`pytest --collect-only`), verified against a clean CI-equivalent environment (`pip install -r requirements.txt`, `pip install flake8 mypy pytest httpx`, matching `.github/workflows/ci.yml`'s `ci` job exactly -- the "httpx" package, not the similarly-named unrelated "httpx2" package a stale CI config once installed by mistake). Coverage spans:

- **`tests/test_utils.py`** -- pure utility functions (`standardize_columns`, `normalize_awc_code`, `fill_missing`, `safe_corr`, `top_bottom`).
- **`tests/test_etl_cleaner.py`** -- the generic loader-stage cleaning pass (`etl/cleaner.py`): column standardization, whitespace stripping, duplicate-row dropping, and that it doesn't mutate its input.
- **`tests/test_district_cube.py`** -- district-name normalization and the actual ten-table merge, checked against both an inline fixture and the committed `data/2025-11` source files (see Results below).
- **`tests/test_pipeline_reconciliation.py`** -- pipeline-wide data-quality gates, run against the committed `data/` and `warehouse/` files: raw-to-warehouse row-count reconciliation per source, referential integrity of the `district` join key against the 30 canonical districts for all ten cube-input sources individually, and consistency of the committed cube artifact against a fresh rebuild (see Results below).
- **`tests/test_models.py`** -- `predict_lbw` / `predict_stunting` return a fitted `RandomForestRegressor`, produce finite predictions, handle missing feature columns, and raise on insufficient data rather than silently misfitting.
- **`tests/test_models_integration.py`** -- runs `predict_lbw` / `predict_stunting` against a real `build_district_cube()` output (not an independently-named fixture), pinning the column-naming seam between the cube builder and the model layer so the two can't silently drift out of sync again (they did once -- see Synthetic Data Provenance below).
- **`tests/test_api.py`** -- FastAPI endpoints via `TestClient`, with `joblib.load` / `pandas.read_csv` mocked so no model files are required to run the suite.

**Plus 11 more, in a separate job, not folded into the 81**: **`tests/test_airflow_dag.py`** parses `dags/poshan_pipeline_dag.py` and checks the resulting DAG object -- task IDs, dependency wiring (`generate` → `[warehouse_etl` + 10 `etl_module__*]` → `cube` → `models`), no cycles, retry config, the month-param default -- without deploying a scheduler or webserver. It needs `apache-airflow` installed, which conflicts with this project's own `pydantic`/FastAPI requirement (`apache-airflow==2.10.5`'s constraints pin `typing-extensions` below what `pydantic-core` needs -- confirmed via `pip check`, not assumed), so it deliberately does **not** run in the same environment as the 81 above, in its own isolated `airflow-dag-integrity` CI job with only `apache-airflow` installed. The main job's `pytest --collect-only` stays at exactly **81**, unchanged, verified directly rather than assumed additive: `test_airflow_dag.py` guards itself with a module-level `pytest.importorskip("airflow", ...)`, and a module-level skip removes the whole file from collection rather than counting its 11 tests as individually skipped (checked: `81 tests collected` in the main environment, not 92 with 11 skipped). Two jobs, two separate counts (81 and 11), reported as two numbers because that's what's actually true of two environments that don't -- and given the confirmed `pip check` conflict, can't -- coexist; see `tests/test_airflow_dag.py`'s own docstring for the full mechanics.

CI runs both jobs (the main suite plus flake8/mypy/three Docker builds, and the isolated DAG-integrity job) on every push to `main`.

## Results: data-quality reconciliation

For an ETL/warehouse pipeline, "evaluation" means checking that the merge didn't silently lose or fabricate data -- not an ML metric. These numbers come from the committed `data/2025-11` and `warehouse/` files (30 districts) -- **synthetic since the data-provenance migration** (see below), but these are structural properties of the pipeline's merge and cleaning logic, not statistics about the underlying figures, so they hold identically whether the source is real or synthetic:

| check | result |
|---|---|
| Row count after merge | 30 -- matches the growth-monitoring (5-6 years) base table exactly, as a left join guarantees |
| Duplicate district keys | 0 |
| Null join keys | 0 |
| Rebuild determinism | Identical output across two runs on the same input, checked directly |
| Per-source district coverage | 9 of 10 sources cover all 30 districts this month |
| Raw-to-warehouse row counts | All 13 committed `data/2025-11` sources reconcile exactly against their `warehouse/etl/2025-11` counterpart (`tests/test_pipeline_reconciliation.py::TestRawToWarehouseRowCountReconciliation`) |
| Referential integrity of `district` | All ten cube-input sources resolve entirely to the 30 canonical districts after cleaning, individually checked (`TestReferentialIntegrity`) |
| Committed cube vs. fresh rebuild | `warehouse/cubes/district_cube_2025-11.csv` matches `build_district_cube("data/2025-11")` exactly, column-for-column and district-for-district (`TestCubeToSourceConsistency`) |

**The one real gap, reported rather than hidden**: the Adolescent Girls (14-18 years) source covers only 10 of the 30 districts this month -- the other 20 districts' `ag_*` columns are correctly `NaN` after the left join, not zero-filled or dropped. `tests/test_district_cube.py::test_adolescent_girls_coverage_gap_matches_documented_value` pins this exact count (20) so a future month's data, or a change to the merge logic, that alters it gets caught rather than silently drifting.

**A second gap the new referential-integrity pass found and fixed**: the raw `(0_to_5_Years)_Growth_Monitoring_11_2025.csv` export appends a state-level "Total" rollup row after the 30 districts. It wasn't affecting the committed cube -- the merge happens to be anchored on a different, Total-free source table -- but any source iterating that table's `district` values directly would have silently treated "Total" as a 31st district. Fixed in `etl/gm_0_5.py` (the row is now dropped before analysis); `TestReferentialIntegrity` pins the fix so it can't regress unnoticed again.

## Synthetic Data Provenance

`data/2025-11` and everything built from it (`warehouse/`, the district cube in all its forms, `models/*.joblib`, `plots/`, `bi_subset_2025_11.csv`, `correlation_pairs.csv`) are **generated, fictional data** -- produced by [`scripts/generate_synthetic_data.py`](scripts/generate_synthetic_data.py), not exported from any real government system. No real district, AWC, Anganwadi worker, or beneficiary is represented anywhere in this repository going forward.

**Reproducing it**: `python scripts/generate_synthetic_data.py --seed 42` (the default). Seeded on Python's `random.Random`; the same seed regenerates byte-identical output, verified directly (two runs, same seed, `diff -r` clean) before this data was committed.

**What's preserved, and why it isn't zero-filled**: the real November 2025 export had genuine structural missingness -- not blank cells, but whole rows and columns that were honestly absent or uncollected. Before that real data was removed from the repo, [`scripts/profile_missingness.py`](scripts/profile_missingness.py) captured those patterns into `data/missingness_profile.json` (schema, coverage rates, district-name lists -- no real figures), which the generator was built against:

- **Adolescent Girls entity-level coverage**: the real report covered only 10 of 30 districts that month. The synthetic version reproduces this as a genuine 10/30 split -- the other 20 districts simply have no row in `Adolescent_Girls_(14_18_Years)_11_2025.csv`, not a zero-filled one. SNP's own `Adolescent Girls` column mirrors the same split (0 for the 20 uncovered districts), matching a real cross-file consistency found in the source data.
- **Anaemia's non-collection-as-zero**: the real `Haemoglobin Measured of Children (6 months - 5 years)` and its `Anaemic` column were exactly 0 for every district while the Pregnant-Women/Lactating-Mother columns in the same file were genuinely populated -- a measurement that was never taken, not a true zero. The generator writes a literal `0` here rather than sampling a small positive number, so it doesn't fabricate a measurement that never happened.
- **Duplicate column names**: Anaemia's real export carries three literal `Anaemic` columns (PW / LM / Child), and `etl/anaemia.py` depends on pandas' positional `.1`/`.2` mangling of that duplicate to route them correctly -- get the count or order wrong and the rename silently no-ops. Reproduced exactly. Growth Monitoring (0-5)'s duplicate `Reference data not found` columns aren't read by any ETL code, but are reproduced anyway for schema fidelity (and always carry the same value in both instances, matching the real export).
- **The state-level "Total" footer row** in Growth Monitoring (0-5) is reproduced, so `etl/gm_0_5.py`'s Total-drop logic (see the reconciliation results above) keeps being exercised by real data shape rather than a synthetic fixture that's "too clean" to need it.
- **Injected, logged anomalies** (`data/synthetic_anomaly_log.csv`): a small, seeded fraction of rows carry deliberate out-of-range values (measured-exceeds-active, percentages outside 0-100, negative counts), calibrated to each file's own plausible ranges -- the same AWC-generator convention used in the sibling `awc-operations-dashboard` project.

**Stated limitation**: this is a single-month dataset. 2025-11 is the only month that has ever existed in this repository's git history or on disk (confirmed by a full `git log --all` sweep before generating anything) -- so unlike the sibling AWC generator, this one does not simulate month-over-month schema drift, row-count changes, or trend data. The pipeline's ability to handle a second real month (a different filename convention, a renamed column, a shifted date range in `etl/home_visit.py`'s hardcoded header text) is untested by this synthetic dataset.

**Real-data reference point**: [`docs/baseline_model_metrics_real_2025-11.json`](docs/baseline_model_metrics_real_2025-11.json) holds one baseline capture of `predict_lbw` / `predict_stunting`'s R², MAE, and feature importances against the real November 2025 ground truth, taken immediately before the data was regenerated as synthetic. It contains aggregate metrics only -- no district names, no per-district predictions, no raw indicator values -- so it's safe to keep as a real-data comparison point through the eventual git-history purge of the real data itself.

## Model Layer Findings

`predict_lbw` and `predict_stunting` fit a `RandomForestRegressor` against a 30-district cross-section (21 train / 9 test rows, `test_size=0.3, random_state=42`) -- the ceiling on this pipeline's real data: every source report is pre-aggregated to district level before export (`SNP_Projections`' `Project`/`Sector`/`AWC` columns are per-district *counts*, not row-level microdata -- confirmed against the real data before it was regenerated as synthetic), and only one month (`2025-11`) has ever existed in this repository's history, so no district×month panel exists either. Both fits are kept in the codebase and covered by tests (`tests/test_models.py`, `tests/test_models_integration.py`) -- the tests confirm they fit and predict without crashing, not that they predict well. What they actually found, evaluated against a mean-predictor baseline and a single-feature linear fit on the same 9-row holdout:

**LBW -- a structured negative result.** R² on the 9-row holdout: mean-predictor baseline -0.283, RandomForest (7 features) -0.192, single-feature linear on `pw_anaemia_rate` alone -0.157. The *ordering* is the finding, not just the sign: added model complexity doesn't buy predictive power here, it costs it -- the RandomForest sits between the trivial baseline and the simpler linear model, beaten by both the model above it in complexity and the one below. Recorded as a sample-size negative result, not cited as a working predictor.

**Stunting -- a leakage-checked correlation, not a validated predictor.** R² on the same 9-row holdout: mean-predictor baseline -0.291, single-feature linear on `suw_ratio` (severely-underweight rate) alone 0.487, full RandomForest (6 features) 0.883. Verified this is not a pipeline data leak: `stunting_total_pct` is computed entirely from the Growth Monitoring (5-6 years) report (`etl/gm_5_6.py`), `suw_ratio` entirely from the SNP Projections report (`etl/snp.py`) -- two independent source files, no shared columns or formula. The correlation is real and stated plainly: severely-underweight rate is strongly associated with stunting rate across these 30 districts (R²≈0.49, linear, one feature), consistent with both indicators reflecting chronic undernutrition. The RandomForest's higher 0.883 is not treated as a stronger version of that same finding -- at n=30 with a 9-row test set, R² is too unstable to support a validated-predictor claim, independent of how clean the leakage check came back.

Full methodology -- the baseline-comparison code, the leakage-check trace, the full-history grain/panel sweep -- in [`docs/model_layer_audit.md`](docs/model_layer_audit.md).

## Airflow DAG (tooling demonstration)

**This pipeline does not need Airflow.** It's a linear, single-machine, single-month chain that runs in seconds -- the "Generate synthetic data" and "Build warehouse (ETL + cube)" steps in `.github/workflows/ci.yml` prove that on every push. [`dags/`](dags/) expresses the same chain as an Airflow DAG to demonstrate orchestration tooling, not because the pipeline's scale demanded it. At this scale a script suffices (and this repo already has several); the DAG's retry/backfill machinery below is illustrative of the pattern, not a fix for a transient-failure or multi-month problem this deterministic, seeded pipeline actually has.

`dags/poshan_pipeline_dag.py`: `generate_synthetic_data` (seed 42) → [`warehouse_etl` + 10 per-source `etl_module__*` tasks, in parallel] → `build_cube` → `train_models`. Retries (2, 2-minute delay), `@monthly` schedule with `catchup=False`, and structural month-parameterization are all present and correctly wired -- and all standard-pattern, not solving a real problem here: `generate_synthetic_data` fails loudly for any month other than `2025-11`, the only one that has ever existed or been profiled (see Synthetic Data Provenance above), rather than fabricating one. `train_models` runs the same `predict_lbw`/`predict_stunting` fits documented in Model Layer Findings above -- running them from a DAG doesn't change what n=30 can support. Full framing, setup, and how to run it (LocalExecutor + docker-compose) in [`docs/airflow_dag.md`](docs/airflow_dag.md).

## Limitations

- Reconciliation was checked against one month of data (November 2025 -- synthetic since the provenance migration, real before it), not a multi-month history -- month-to-month stability of these numbers (e.g. whether the Adolescent Girls gap recurs, worsens, or is specific to this month) isn't measured here, and the synthetic generator doesn't attempt to simulate it (see Synthetic Data Provenance).
- The Adolescent Girls coverage gap is reported, not root-caused: whether it reflects a genuine reporting gap at those 20 districts, a filename/format mismatch in the source export, or something else in the ten-source pipeline isn't investigated in this pass.
- Test coverage is real but uneven across the pipeline: the shared cleaning utilities, the district-cube merge, the prediction models, the API layer, and now each of the ten individual per-source `etl/` transformation modules' district-key output are all covered; the non-district-key columns those modules derive (e.g. the stunting/underweight ratios) are still only exercised indirectly through the cube-build integration test, not with dedicated per-column unit tests.

## Container Setup

`Dockerfile.api`, `Dockerfile.etl`, `Dockerfile.cube`, and `docker-compose.yml` support containerized runs of each pipeline component; CI builds all three images on every push.

## Data Notes

The workflow expects monthly local source CSV files organized by month folders (`data/YYYY-MM/`) and produces cube/warehouse outputs keyed to that same month tag.

## Project Scope

ETL-driven Poshan analytics over public-scale AWC reporting data: district cube generation, correlation analysis, lightweight predictive modeling, and a FastAPI serving layer over the result.

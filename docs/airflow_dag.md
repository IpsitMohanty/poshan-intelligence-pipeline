# Airflow DAG (tooling demonstration)

**Read this before running anything here.** This pipeline is a linear, single-machine, single-month chain that runs in seconds -- generate synthetic data, run the ETL, build the cube, done (see `.github/workflows/ci.yml`'s "Generate synthetic data" and "Build warehouse (ETL + cube)" steps, or just run `pytest -v` locally). It does **not** need Airflow, a scheduler, distributed retries, or any of the machinery below. This directory exists to demonstrate orchestration tooling -- expressing an existing pipeline as a properly-wired DAG -- not because the pipeline's scale demanded it. If you're evaluating this repo for orchestration *need*, the honest answer is: it doesn't have any yet; if you're evaluating it for orchestration *familiarity*, that's what this is for.

Same framing lives in [`dags/poshan_pipeline_dag.py`](../dags/poshan_pipeline_dag.py)'s module docstring and the main [`README.md`](../README.md)'s "Airflow DAG" section -- not repeated differently in three places by accident.

## What's here

- [`dags/poshan_pipeline_dag.py`](../dags/poshan_pipeline_dag.py) -- the DAG: `generate_synthetic_data` (seed 42) → [`warehouse_etl` + 10 per-source `etl_module__*` tasks, in parallel] → `build_cube` → `train_models`. Same chain `.github/workflows/ci.yml` already runs green, plus a models step CI doesn't run. Deliberately a top-level `dags/` directory, not `airflow/dags/` -- a directory literally named `airflow` shadows the `apache-airflow` package itself once the repo root is on `sys.path` (which both pytest and this setup's own `PYTHONPATH` do) -- see that file's module docstring for how this was actually found (not just anticipated).
- [`Dockerfile.airflow`](../Dockerfile.airflow) -- extends the official `apache/airflow:2.10.5-python3.12` image with this project's own `requirements.txt` and a `PYTHONPATH=/opt/airflow/project` pointing at where `docker-compose.airflow.yaml` bind-mounts the rest of the repo. Both halves are required for task callables to actually import `etl.*` / `cubes.*` / `analytics.*` at execution time -- an earlier version of this setup only had the `pip install` half and the bind mount was missing entirely, which parsed fine but failed every task from `generate_synthetic_data` onward at actual execution (`can't open file '/opt/airflow/scripts/generate_synthetic_data.py'`) -- found by triggering a real run, not caught by DAG parsing or `docker build` alone. Flat, repo-root naming, matching the existing `Dockerfile.etl` / `Dockerfile.cube` / `Dockerfile.api` convention rather than inventing a new one.
- [`docker-compose.airflow.yaml`](../docker-compose.airflow.yaml) -- LocalExecutor stack (Postgres + webserver + scheduler), trimmed from [Airflow's official reference compose](https://airflow.apache.org/docs/apache-airflow/2.10.5/docker-compose.yaml). No Redis, no Celery worker, no Flower -- LocalExecutor runs tasks as local subprocesses of the scheduler, which is already more than this pipeline needs, not less. A sibling file to `docker-compose.yml`, not merged into it -- this stack is meaningfully heavier than the pipeline itself needs to run. Bind-mounts the whole repo root at `/opt/airflow/project` in one mount (plus `dags/` separately, at `/opt/airflow/dags`, Airflow's own `DAGS_FOLDER` convention) -- see `PROJECT_ROOT` in this file and `dags/poshan_pipeline_dag.py`'s `_repo_root()` for why the DAG needs to be told that explicitly rather than infer it from its own file location.

## Running it

```bash
docker compose -f docker-compose.airflow.yaml up airflow-init   # one-time: DB migrate + create the airflow/airflow admin user
docker compose -f docker-compose.airflow.yaml up                # webserver on http://localhost:8080, scheduler alongside it
```

The DAG ships unpaused (`is_paused_upon_creation=False`) so triggering it doesn't need a manual unpause first -- that setting only takes effect the first time Airflow's metadata DB sees this DAG, though, so if you're re-running against a Postgres volume from before this was added, `docker compose -f docker-compose.airflow.yaml exec airflow-scheduler airflow dags unpause poshan_intelligence_pipeline` once will do the same thing.

Trigger `poshan_intelligence_pipeline` from the UI (or `airflow dags trigger poshan_intelligence_pipeline` from inside the scheduler container) with the default `month=2025-11` param. Output lands in `data/2025-11/`, `warehouse/`, and `models/` on the host -- same bind-mount convention `docker-compose.yml` uses for the `etl`/`cube`/`api` services, just arriving via the one whole-repo mount above rather than three separate ones.

**Single-month manual backfill**, the one meaningful backfill this DAG supports:

```bash
docker compose -f docker-compose.airflow.yaml run airflow-scheduler airflow dags backfill \
  poshan_intelligence_pipeline -s 2025-11-01 -e 2025-11-02
```

Running it for any other month fails loudly, on purpose -- see the next section.

## Why the retry/backfill/scheduling machinery is illustrative, not load-bearing

- **Retries + `retry_delay`** (2 retries, 2-minute delay, every task): the standard Airflow default_args pattern, not tuned against any observed transient failure -- this pipeline is deterministic and seeded; the same input always produces the same output, so there's no flaky external dependency for a retry to meaningfully paper over. Included to show the pattern wired up correctly.
- **`@monthly` schedule + `catchup=False`**: standard scheduling config. `catchup=False` specifically because auto-backfilling every month between `start_date` and now would fabricate runs for months that never had real (or profiled-synthetic) data -- see the next point.
- **Month parameterization**: the DAG takes a `month` param (default, and only supported value, `2025-11`) and every task derives its paths from it -- structurally correct, general parameterization. But `generate_synthetic_data` raises immediately for any other month, rather than silently producing something. `scripts/generate_synthetic_data.py`'s `MONTH_LABEL`, filenames, and `etl/home_visit.py`'s hardcoded date-range text are all specific to November 2025 because that's the one real government export `scripts/profile_missingness.py` ever profiled (see the main README's "Synthetic Data Provenance" section). A second month is real work -- profile a real export the same way -- not a config flag this DAG can flip.
- **Idempotent re-runs**: every task overwrites its output deterministically (the generator from its seed, the ETL/cube steps via `to_csv`), so retries and repeated manual runs don't accumulate state or duplicate rows. This is a genuine, useful property -- not illustrative -- it's just also true of the underlying scripts with or without Airflow running them.

## Models step

`train_models` runs `analytics.models.predict_lbw` / `predict_stunting` -- the same `RandomForestRegressor` fits that have always been in this repo -- against the cube this DAG just built, and saves the resulting `.joblib` files. This does not imply production prediction: see the main README's "Model Layer Findings" section and `docs/model_layer_audit.md` for why both fits are documented as a small-sample negative result (LBW) and a leakage-checked correlation (stunting), not validated predictors, at n=30. Running them from a DAG instead of a script doesn't change what n=30 can support.

## Testing without deploying the stack

`tests/test_airflow_dag.py` parses `dags/poshan_pipeline_dag.py` and checks the resulting `DAG` object directly -- task IDs, dependency wiring, no cycles, retry config, the month-param default -- without a scheduler, webserver, or Postgres. This is what CI runs, in its own `airflow-dag-integrity` job, kept separate from the main test job: `apache-airflow==2.10.5`'s pinned constraints conflict with this project's own `pydantic`/FastAPI requirement (confirmed via `pip check`, not assumed -- see that test file's docstring), so `apache-airflow` is never installed alongside `requirements.txt`. See the main README's Tests section for how the two jobs' counts are reported.

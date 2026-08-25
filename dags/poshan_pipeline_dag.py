"""Airflow DAG wrapping the existing Poshan Intelligence pipeline.

WHY THIS EXISTS -- read before citing it anywhere: this pipeline is a
linear, single-machine, single-month chain that runs in seconds (see the
"Generate synthetic data" + "Build warehouse (ETL + cube)" steps in
.github/workflows/ci.yml, or just run `pytest -v` -- the whole thing,
generation through tests, takes well under a minute). It does NOT
require Airflow, Celery workers, distributed retries, or a scheduler.
This DAG demonstrates orchestration tooling; it does not claim the
pipeline needed it. The retry/backfill/scheduling machinery below is the
standard Airflow pattern, included to show the pattern correctly wired
up -- it is illustrative, not a fix for a failure mode this deterministic,
seeded pipeline actually has. See docs/airflow_dag.md and the README's
"Airflow DAG" section for the same framing in prose.

CHAIN (matches what CI already runs green, plus a models step CI
doesn't run):
    generate_synthetic_data (seed 42)
        -> [warehouse_etl, 10 per-source etl-module validation tasks]  (parallel)
        -> build_cube
        -> train_models

MONTH PARAMETERIZATION, HONESTLY: the DAG accepts a `month` param
(default "2025-11", the only month whose synthetic generator, missingness
profile, and filename/date-range quirks actually exist -- see
scripts/generate_synthetic_data.py's hardcoded MONTH_LABEL and
README.md's "Synthetic Data Provenance" section). The DAG is structurally
month-parameterized -- every task derives its paths from `month`, and a
single-month manual backfill for 2025-11 is a real, meaningful thing to
run -- but `generate_synthetic_data` deliberately fails loudly for any
other month rather than silently fabricating data that was never
profiled. This is not a TODO to "add more months later" without more
work: a second month would need its own real export to profile missingness
against, same as 2025-11 did.

IMPORTS: every project-module import (etl.*, cubes.*, analytics.*, pandas
transitively) is deferred to inside each task callable, not at module top
level. This is standard Airflow practice regardless (the scheduler
re-parses every DAG file on a short interval; expensive imports at module
scope slow that down for no benefit), and it also means this file -- and
the DAG-integrity test that imports it -- only needs `apache-airflow`
installed, not the project's own (much heavier, separately-versioned)
dependency set. Task execution needs both; see Dockerfile.airflow.

NAMING NOTE: this file lives in a top-level dags/ directory, not
airflow/dags/. It didn't start that way -- the first version of this DAG
did live under a top-level airflow/ directory, and that was the actual,
found-not-anticipated bug: a top-level directory literally named
"airflow" shadows the apache-airflow package itself as a Python 3
implicit namespace package whenever the repo root is on sys.path (which
pytest, and this project's own PYTHONPATH convention via
Dockerfile.airflow, both do). This surfaced as `from airflow import DAG`
failing with `ImportError: cannot import name 'DAG' from 'airflow'
(unknown location)` -- a confusing failure, not the clean
ModuleNotFoundError you'd expect if apache-airflow just weren't
installed -- when tests/test_airflow_dag.py was actually run against the
project's main environment (which has no apache-airflow installed, so it
should have skipped cleanly) during development. Not something reasoned
out in advance and designed around; the airflow/ -> dags/ rename below
happened only after that run surfaced it.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

# The only month that has ever existed in this repo, real or synthetic --
# see README.md's "Synthetic Data Provenance" > Stated limitation.
ONLY_SUPPORTED_MONTH = "2025-11"

# One task per etl/ module with its own dedicated per-source analyze_*
# function (ten of the pipeline's 13 real source files -- the other three,
# AWC_Staff / VHSND_and_CBE / Measurement Efficiency Status, are cleaned
# generically by the warehouse_etl task instead; see README.md's Approach
# section for the same 10-vs-13 accounting). key -> (source filename,
# "etl.module:function" to import lazily inside the task).
ETL_MODULES = {
    "gm_0_5": ("(0_to_5_Years)_Growth_Monitoring_11_2025.csv", "etl.gm_0_5", "analyze_gm_0_5"),
    "gm_5_6": ("(5_to_6_Years)_Growth_Monitoring_11_2025.csv", "etl.gm_5_6", "analyze_gm_5_6"),
    "anaemia": ("Anaemia_11_2025.csv", "etl.anaemia", "analyze_anaemia"),
    "lbw": ("Low_Birth_Weight_11_2025.csv", "etl.lbw", "analyze_lbw"),
    "gwg": ("Gestational_Weight_Gain_Report_11_2025.csv", "etl.gwg", "analyze_gwg"),
    "ag": ("Adolescent_Girls_(14_18_Years)_11_2025.csv", "etl.adolescent_girls", "analyze_adolescent_girls"),
    "me": ("Measuring_Efficiency_Children_0_to_6_years_11_2025.csv", "etl.measuring_efficiency", "analyze_me"),
    "hv": ("Home_Visit_11_2025.csv", "etl.home_visit", "analyze_home_visit"),
    "snp": ("SNP_Projections_12_2025.csv", "etl.snp", "analyze_snp"),
    "awc": ("AWC_11_2025.csv", "etl.awc_summary", "analyze_awc_summary"),
}


def _month(context) -> str:
    return context["params"]["month"]


def _repo_root():
    import os
    from pathlib import Path

    # In the Airflow container, dags/ is bind-mounted at /opt/airflow/dags
    # while the rest of the project is bind-mounted SEPARATELY at
    # /opt/airflow/project (docker-compose.airflow.yaml) - they are not
    # siblings under a shared parent directory inside the container the
    # way they are on the host (or in CI, where this function is never
    # actually called - the DAG-integrity test only parses the DAG, never
    # executes a task). Found by actually running the DAG, not reasoned
    # out in advance: the file-relative computation below silently gave
    # /opt/airflow as "repo root" in-container, and
    # /opt/airflow/scripts/generate_synthetic_data.py doesn't exist -
    # `can't open file '/opt/airflow/scripts/generate_synthetic_data.py':
    # No such file or directory`. PROJECT_ROOT (set in
    # docker-compose.airflow.yaml) overrides explicitly for that case.
    override = os.environ.get("PROJECT_ROOT")
    if override:
        return Path(override)
    # dags/poshan_pipeline_dag.py -> repo root is one level up. Correct
    # for local dev and CI, where dags/'s parent genuinely is repo root.
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------
# Task callables
# ---------------------------------------------------------------------
def generate_synthetic_data(**context):
    """Seeded synthetic data, same command CI runs
    (`python scripts/generate_synthetic_data.py --seed 42`). Idempotent:
    the generator overwrites its output directory deterministically from
    the seed, so re-running this task (retry, or a repeated manual
    backfill) reproduces byte-identical files rather than accumulating
    state."""
    import subprocess
    import sys

    month = _month(context)
    if month != ONLY_SUPPORTED_MONTH:
        # Loud and specific, not a silent skip: the generator's
        # MONTH_LABEL, filenames, and home_visit's hardcoded date-range
        # text are all hardcoded to November 2025 because that's the one
        # real export scripts/profile_missingness.py ever profiled. A
        # second month needs its own real export profiled the same way
        # before this generator could honestly produce it -- see
        # README.md's Synthetic Data Provenance > Stated limitation.
        raise AirflowException(
            f"generate_synthetic_data does not support month={month!r}. "
            f"Only {ONLY_SUPPORTED_MONTH!r} has a profiled missingness spec "
            "for the generator to reproduce; adding another month is real "
            "work (profile a real export first), not a config change."
        )

    repo_root = _repo_root()
    out_dir = repo_root / "data" / month
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "generate_synthetic_data.py"),
         "--seed", "42", "--output-dir", str(out_dir)],
        cwd=str(repo_root), capture_output=True, text=True,
    )
    logger.info(result.stdout)
    if result.returncode != 0:
        logger.error(result.stderr)
        raise AirflowException(f"generate_synthetic_data.py failed (exit {result.returncode})")


def run_warehouse_etl(**context):
    """The generic loader+cleaner pass over all 13 raw source files
    (etl.run_month.run_etl_for_month -- the same function
    `python -m etl.run_month` calls in CI), writing warehouse/etl/<month>/.
    Idempotent: to_csv overwrites per-file, no accumulation across runs."""
    from pathlib import Path

    from etl.run_month import run_etl_for_month

    month = _month(context)
    repo_root = _repo_root()
    run_etl_for_month(
        Path(repo_root / "data" / month),
        Path(repo_root / "warehouse" / "etl" / month),
    )


def make_etl_module_task_callable(source_filename: str, module_path: str, func_name: str):
    """Returns a task callable that imports and runs one etl module's
    analyze_* function directly against the month's raw source file --
    the same function cubes.district_cube.build_district_cube() calls
    internally when it builds the cube. Run here too, as its own task,
    to give each of the 10 per-source modules real, independent
    pass/fail/retry status and a genuine parallel fan-out in the graph --
    not to precompute anything the cube step reuses (build_district_cube
    re-derives these tables itself; see this file's module docstring and
    docs/airflow_dag.md for why that duplication was left as-is rather than
    refactored to thread outputs between tasks)."""

    def _run(**context):
        import importlib

        month = _month(context)
        repo_root = _repo_root()
        source_path = repo_root / "data" / month / source_filename

        module = importlib.import_module(module_path)
        analyze_fn = getattr(module, func_name)
        df = analyze_fn(str(source_path))
        logger.info("%s: %d rows, %d columns from %s", func_name, len(df), len(df.columns), source_filename)
        if df.empty:
            raise AirflowException(f"{func_name} produced an empty table from {source_filename}")

    return _run


def build_cube(**context):
    """cubes.district_cube.build_district_cube() -- the same function
    `python -m cubes.run_cube` calls in CI -- run against data/<month>
    (it reads the raw source files directly, independent of
    warehouse/etl/<month>/; see cubes/district_cube.py). Depends on the
    warehouse_etl task and all 10 etl-module tasks in this DAG, matching
    CI's own step ordering (etl.run_month then cubes.run_cube in the
    same "Build warehouse" step) even though build_district_cube doesn't
    technically read warehouse_etl's output -- kept sequential here to
    mirror CI exactly rather than claim a reordering CI doesn't do.
    Writes warehouse/cubes/district_cube_<month-with-dashes>.csv,
    overwriting on re-run (idempotent)."""
    from pathlib import Path

    from cubes.district_cube import build_district_cube

    month = _month(context)
    repo_root = _repo_root()
    cube_df = build_district_cube(str(repo_root / "data" / month))

    out_dir = repo_root / "warehouse" / "cubes"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"district_cube_{month}.csv"
    cube_df.to_csv(out_path, index=False)
    logger.info("Cube written: %s (%d rows, %d columns)", out_path, *cube_df.shape)


def train_models(**context):
    """analytics.models.predict_lbw / predict_stunting -- the same
    RandomForestRegressor fits analytics/models.py always did -- run
    against the cube this DAG just built. This is the orchestration
    pattern for a model-training step, not a production prediction
    claim: n=30 (districts) is this pipeline's real ceiling regardless
    of how the step is triggered, and both fits are already documented
    in README.md's "Model Layer Findings" as a small-sample negative
    result (LBW) and a leakage-checked correlation (stunting), not
    validated predictors. Saving the resulting joblib artifacts here
    doesn't change that framing -- see docs/model_layer_audit.md."""
    from pathlib import Path

    import joblib
    import pandas as pd

    from analytics.models import predict_lbw, predict_stunting

    month = _month(context)
    repo_root = _repo_root()
    cube_path = repo_root / "warehouse" / "cubes" / f"district_cube_{month}.csv"
    df = pd.read_csv(cube_path)

    models_dir = repo_root / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    lbw_model, _, _ = predict_lbw(df)
    joblib.dump(lbw_model, models_dir / "lbw_model.joblib")

    stunting_model, _, _ = predict_stunting(df)
    joblib.dump(stunting_model, models_dir / "stunting_model.joblib")

    logger.info("Models saved to %s", models_dir)


# ---------------------------------------------------------------------
# DAG
# ---------------------------------------------------------------------
default_args = {
    # Standard Airflow defaults, not a response to an observed failure
    # mode -- see this file's module docstring. Kept small (2 retries,
    # 2-minute delay) because they're illustrative of the pattern, not
    # tuned against any real transient-failure history this deterministic
    # pipeline has ever produced.
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="poshan_intelligence_pipeline",
    description=(
        "Orchestration-tooling demo over the existing Poshan Intelligence "
        "pipeline (generate -> etl -> cube -> models). Illustrative: this "
        "pipeline does not require Airflow at its current scale -- see "
        "this file's module docstring and docs/airflow_dag.md."
    ),
    default_args=default_args,
    schedule="@monthly",
    start_date=datetime(2025, 11, 1),
    catchup=False,
    max_active_runs=1,
    params={"month": ONLY_SUPPORTED_MONTH},
    tags=["demo", "poshan", "orchestration-tooling"],
    # Airflow pauses every newly-discovered DAG by default; found by
    # actually triggering this one - the first run just sat queued
    # because the DAG itself was paused, not because of any task issue.
    # docs/airflow_dag.md's "trigger it" instructions should work without
    # a manual unpause step first.
    is_paused_upon_creation=False,
) as dag:

    t_generate = PythonOperator(
        task_id="generate_synthetic_data",
        python_callable=generate_synthetic_data,
    )

    t_warehouse_etl = PythonOperator(
        task_id="warehouse_etl",
        python_callable=run_warehouse_etl,
    )

    etl_module_tasks = [
        PythonOperator(
            task_id=f"etl_module__{key}",
            python_callable=make_etl_module_task_callable(fname, module_path, func_name),
        )
        for key, (fname, module_path, func_name) in ETL_MODULES.items()
    ]

    t_cube = PythonOperator(
        task_id="build_cube",
        python_callable=build_cube,
    )

    t_models = PythonOperator(
        task_id="train_models",
        python_callable=train_models,
    )

    # generate -> [warehouse_etl, the 10 etl-module tasks] (parallel) -> cube -> models
    t_generate >> t_warehouse_etl
    t_generate >> etl_module_tasks
    [t_warehouse_etl, *etl_module_tasks] >> t_cube
    t_cube >> t_models

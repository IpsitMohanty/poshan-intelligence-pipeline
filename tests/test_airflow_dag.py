"""Coverage: dags/poshan_pipeline_dag.py -- structural validation
only (imports cleanly, no cycles, dependencies wired as intended, retry/
schedule config present). This is the standard Airflow "DAG-integrity"
pattern: parse the DAG module and inspect the resulting airflow.DAG
object, without deploying a scheduler, webserver, or metadata database.
No task is actually executed here -- see docs/airflow_dag.md for how to
run the real thing via docker-compose.

Runs in its own, separate CI job (`airflow-dag-integrity` in
.github/workflows/ci.yml), NOT the main job's environment. Checked
directly, not assumed: apache-airflow==2.10.5's pinned constraints force
typing-extensions down to 4.12.2, which conflicts with pydantic/
pydantic-core (FastAPI's dependency) requiring >=4.14.1 -- confirmed via
`pip check` after installing both apache-airflow and this project's own
requirements.txt into one environment, not just eyeballed. So this file
is deliberately kept out of the main test job's environment (apache-
airflow is never installed there) and gets its own isolated one instead.

This is possible cleanly because every project-module import inside
poshan_pipeline_dag.py's task callables (etl.*, cubes.*, analytics.*) is
deferred to inside those callables, not at module top level (see that
file's own docstring) -- importing the DAG module here only exercises
apache-airflow's own import surface, nothing from requirements.txt.

In the MAIN test job (no apache-airflow installed), the module-level
`pytest.importorskip` guard right below skips this whole FILE as one
collection unit before any of the 11 test functions below are even
enumerated -- checked directly: the main job's `pytest --collect-only`
reports exactly 81, not 92-with-11-skipped. That's why the main suite's
published count and this file's count are reported as two separate
numbers rather than added into one "N passed" figure; see README.md's
Tests section.
"""
import sys
from pathlib import Path

import pytest

AIRFLOW_DAGS_DIR = Path(__file__).resolve().parent.parent / "dags"

pytest.importorskip("airflow", reason="apache-airflow not installed in this environment")

sys.path.insert(0, str(AIRFLOW_DAGS_DIR))
import poshan_pipeline_dag as dag_module  # noqa: E402

EXPECTED_ETL_MODULE_TASK_IDS = {
    f"etl_module__{key}" for key in [
        "gm_0_5", "gm_5_6", "anaemia", "lbw", "gwg", "ag", "me", "hv", "snp", "awc",
    ]
}


@pytest.fixture(scope="module")
def dag():
    return dag_module.dag


def test_dag_loads_with_no_import_errors(dag):
    # If poshan_pipeline_dag imported at all (see module-level import
    # above), this already passed - asserting it explicitly documents
    # the intent as a named test rather than relying on collection-time
    # failure alone.
    assert dag is not None


def test_dag_id_and_schedule(dag):
    assert dag.dag_id == "poshan_intelligence_pipeline"
    assert dag.timetable.summary == "@monthly" or "monthly" in str(dag.schedule_interval).lower()
    assert dag.catchup is False, "catchup=False: don't silently backfill months that were never real"


def test_dag_has_no_cycles(dag):
    # airflow.utils.dag_cycle_tester.check_cycle raises AirflowDagCycleException
    # if a cycle exists (the DAG constructor already runs this implicitly at
    # parse time in practice - if poshan_pipeline_dag imported at all, per
    # test_dag_loads_with_no_import_errors, there wasn't one - but check it
    # explicitly and directly rather than relying on that as a side effect).
    from airflow.utils.dag_cycle_tester import check_cycle

    check_cycle(dag)


def test_month_param_defaults_to_the_only_real_month(dag):
    assert dag.params["month"] == "2025-11"


def test_expected_task_ids_present(dag):
    task_ids = set(dag.task_ids)
    expected = {"generate_synthetic_data", "warehouse_etl", "build_cube", "train_models"} | EXPECTED_ETL_MODULE_TASK_IDS
    assert expected <= task_ids
    assert len(task_ids) == len(expected), f"unexpected extra tasks: {task_ids - expected}"


def test_generate_is_the_root_task(dag):
    t = dag.get_task("generate_synthetic_data")
    assert t.upstream_task_ids == set()


def test_warehouse_etl_and_etl_modules_depend_only_on_generate(dag):
    for task_id in {"warehouse_etl"} | EXPECTED_ETL_MODULE_TASK_IDS:
        t = dag.get_task(task_id)
        assert t.upstream_task_ids == {"generate_synthetic_data"}, task_id


def test_cube_depends_on_warehouse_etl_and_every_etl_module(dag):
    t = dag.get_task("build_cube")
    assert t.upstream_task_ids == {"warehouse_etl"} | EXPECTED_ETL_MODULE_TASK_IDS


def test_models_depends_only_on_cube(dag):
    t = dag.get_task("train_models")
    assert t.upstream_task_ids == {"build_cube"}


def test_retries_and_retry_delay_are_set(dag):
    for task in dag.tasks:
        assert task.retries == 2, task.task_id
        assert task.retry_delay.total_seconds() == 120, task.task_id


def test_generate_task_rejects_unsupported_months():
    """Structural honesty check, not a run: the callable must exist and
    must be the one that raises for month != 2025-11 - pinned so this
    can't silently regress into fabricating data for a month that was
    never profiled. Calls the callable directly (no Airflow context
    machinery needed for this one - it fails before touching context
    beyond the month key)."""
    from airflow.exceptions import AirflowException

    with pytest.raises(AirflowException, match="2025-11"):
        dag_module.generate_synthetic_data(params={"month": "2025-12"})

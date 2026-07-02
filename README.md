# Poshan Intelligence Pipeline

[![CI](https://github.com/IpsitMohanty/poshan-intelligence-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/IpsitMohanty/poshan-intelligence-pipeline/actions/workflows/ci.yml)

Multi-stage **Poshan / AWC analytics pipeline** that combines ETL, district-level cube generation, correlation analysis, basic predictive modeling, FastAPI endpoints, and analytical visuals.

This repository is structured as a local intelligence workflow over operational nutrition and Anganwadi reporting data rather than a single notebook or one-off script.

## What This Project Does

The project builds a district-level analytical layer from multiple operational CSV sources and supports several downstream uses.

It includes:

- ETL modules for multiple Poshan / AWC reporting streams
- district-level cube generation from monthly source data
- correlation analysis over operational and nutrition indicators
- simple predictive modeling for measures such as low birth weight and stunting
- a FastAPI layer for serving model and district insights
- chart and BI subset generation for analytical review

## Architecture

Monthly source CSVs -> ETL modules -> district cube -> analytics / models / visuals -> API and analytical outputs

## Repository Structure

- `etl/`
  Source-specific transformation logic for reporting streams such as adolescent girls, anaemia, AWC summary, home visits, LBW, measuring efficiency, SNP, and related modules.

- `cubes/`
  District cube construction logic and generated district-level cube outputs.

- `analytics/`
  Correlation, visualization, and model helper modules.

- `api/`
  FastAPI app and request schemas for model predictions and district insights.

- `models/`
  Serialized trained model artifacts.

- `plots/`
  Exported analytical charts such as top/bottom bars, scatter plots, and correlation heatmaps.

- `data/`
  Local monthly source data folders used by the ETL and cube-building steps.

## Main Files

- `main.py`
  Builds the district cube from a monthly data folder and exports it to CSV.

- `models_runner.py`
  Loads the latest cube, trains or runs model workflows, and saves predictions / model outputs.

- `correlate.py`
  Runs correlation reporting.

- `visuals.py`
  Generates visual outputs and BI subsets.

- `docker-compose.yml`
  Multi-service container orchestration for the project components.

- `Dockerfile.api`
  API container definition.

- `Dockerfile.etl`
  ETL container definition.

- `Dockerfile.cube`
  Cube-generation container definition.

## Example Outputs

The repository currently contains outputs such as:

- district cube CSVs
- BI subset CSVs
- correlation pair reports
- exported plots
- saved model artifacts

## Tech Stack

- Python
- Pandas
- scikit-learn
- FastAPI
- Uvicorn
- Joblib
- Matplotlib
- Seaborn
- Docker / Docker Compose

## Testing

The project includes a pytest suite covering three areas:

**`tests/test_utils.py`** — unit tests for pure utility functions
- `standardize_columns`: whitespace stripping, lowercase, special-char removal
- `normalize_awc_code`: left-pads codes to 11 digits
- `fill_missing`: zero, ffill, and unknown strategy behaviour
- `safe_corr`: matrix shape, diagonal identity, sign correctness
- `top_bottom`: correct boundary values for n-largest / n-smallest

**`tests/test_models.py`** — trains `predict_lbw` and `predict_stunting` on synthetic district data
- Verifies a `RandomForestRegressor` is returned and predictions are finite
- Checks that missing feature columns are handled gracefully (filtered at training time)
- Confirms feature importances sum to 1.0
- Asserts that insufficient data raises rather than silently misfitting

**`tests/test_api.py`** — FastAPI endpoint tests via `TestClient` with mocked `joblib.load` and `pandas.read_csv` (no model files required)
- `GET /` returns 200
- `POST /predict/lbw` and `POST /predict/stunting` return floats
- `POST /predict/lbw` with no valid features returns 400
- `GET /district/{name}` returns 200 for a known district and 404 for an unknown one
- `GET /district_structured/{name}` response contains all expected top-level keys

Run the suite with:

```bash
pytest -v
```

CI runs tests on every push to `main` and fails the build if any test fails.

## Running Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Build the district cube:

```bash
python main.py
```

Run correlation analysis:

```bash
python correlate.py
```

Generate visuals:

```bash
python visuals.py
```

Run the API:

```bash
uvicorn api.main:app --reload
```

## Container Setup

The repository includes:

- `Dockerfile.api`
- `Dockerfile.etl`
- `Dockerfile.cube`
- `docker-compose.yml`

These support containerized runs for the API and pipeline components.

## Data Notes

The workflow expects monthly local source CSV files organized by month folders and uses file paths / outputs built around local execution.

## Project Scope

This repository is focused on ETL-driven Poshan analytics, district cube generation, model experimentation, and lightweight API exposure over operational datasets.

# 📦 Project Structure Report — poshan_intelligence


## 📁 Folder: `.`

### `bi_subset_2025_11.csv` (non-python file)

### `correlate.py`

**Imports:** analytics.correlations, pandas

**Functions:** main

**Classes:** 

### `dependency_graph.json` (non-python file)

### `district_cube_2025_11.csv` (non-python file)

### `introspect.py`

**Imports:** ast, json, os, pathlib

**Functions:** analyze_python_file, scan_project, generate_markdown_report, save_dependency_graph

**Classes:** 

### `main.py`

**Imports:** cubes.district_cube

**Functions:** 

**Classes:** 

### `models_runner.py`

**Imports:** analytics.models, datetime, joblib, pandas, pathlib

**Functions:** load_latest_cube, save_model, save_predictions, run_all_models

**Classes:** 

### `project_report.md` (non-python file)

### `requirements.txt` (non-python file)

### `visuals.py`

**Imports:** analytics.visualize, os

**Functions:** main

**Classes:** 


## 📁 Folder: `analytics`

### `correlations.py`

**Imports:** pandas

**Functions:** correlation_report

**Classes:** 

### `models.py`

**Imports:** pandas, sklearn.ensemble, sklearn.metrics, sklearn.model_selection

**Functions:** _train_model, predict_lbw, predict_stunting

**Classes:** 

### `visualize.py`

**Imports:** matplotlib.pyplot, os, pandas

**Functions:** load_cube, plot_top_bottom_bar, plot_scatter, plot_corr_heatmap, export_bi_subset

**Classes:** 

### `__init__.py`

**Imports:** 

**Functions:** 

**Classes:** 


## 📁 Folder: `analytics\__pycache__`

### `correlations.cpython-313.pyc` (non-python file)

### `models.cpython-313.pyc` (non-python file)

### `visualize.cpython-313.pyc` (non-python file)

### `__init__.cpython-313.pyc` (non-python file)


## 📁 Folder: `api`

### `main.py`

**Imports:** api.schemas, fastapi, joblib, pandas, pathlib

**Functions:** root, predict_lbw, predict_stunting, district_insights

**Classes:** 

### `schemas.py`

**Imports:** pydantic

**Functions:** 

**Classes:** PredictRequest


## 📁 Folder: `api\__pycache__`

### `main.cpython-313.pyc` (non-python file)

### `schemas.cpython-313.pyc` (non-python file)


## 📁 Folder: `cubes`

### `awc_cube.py`

**Imports:** 

**Functions:** 

**Classes:** 

### `district_cube.py`

**Imports:** etl.adolescent_girls, etl.anaemia, etl.awc_summary, etl.gm_5_6, etl.gwg, etl.home_visit, etl.lbw, etl.measuring_efficiency, etl.snp, pandas

**Functions:** clean_district, build_district_cube

**Classes:** 

### `predictions_district_cube_2025_11_20251204_1555.csv` (non-python file)


## 📁 Folder: `cubes\__pycache__`

### `district_cube.cpython-313.pyc` (non-python file)


## 📁 Folder: `data`

_No files_


## 📁 Folder: `data\2025-11`

### `(5_to_6_Years)_Growth_Monitoring_11_2025.csv` (non-python file)

### `Adolescent_Girls_(14_18_Years)_11_2025.csv` (non-python file)

### `Anaemia_11_2025.csv` (non-python file)

### `AWC_11_2025.csv` (non-python file)

### `AWC_Staff_11_2025.csv` (non-python file)

### `Gestational_Weight_Gain_Report_11_2025.csv` (non-python file)

### `Home_Visit_11_2025.csv` (non-python file)

### `Low_Birth_Weight_11_2025.csv` (non-python file)

### `Measurement_Efficiency_Status_11_2025 (1).csv` (non-python file)

### `Measuring_Efficiency_Children_0_to_6_years_11_2025.csv` (non-python file)

### `SNP_Projections_12_2025.csv` (non-python file)

### `VHSND_and_CBE_11_2025.csv` (non-python file)


## 📁 Folder: `downloads`

_No files_


## 📁 Folder: `downloads\2025-11`

_No files_


## 📁 Folder: `etl`

### `adolescent_girls.py`

**Imports:** etl.loader, pandas

**Functions:** analyze_adolescent_girls

**Classes:** 

### `anaemia.py`

**Imports:** etl.loader, pandas

**Functions:** analyze_anaemia

**Classes:** 

### `awc_summary.py`

**Imports:** etl.loader, pandas

**Functions:** analyze_awc_summary

**Classes:** 

### `cleaner.py`

**Imports:** 

**Functions:** 

**Classes:** 

### `gm_5_6.py`

**Imports:** etl.loader, pandas

**Functions:** analyze_gm_5_6

**Classes:** 

### `gwg.py`

**Imports:** etl.loader, pandas

**Functions:** analyze_gwg

**Classes:** 

### `home_visit.py`

**Imports:** etl.loader, pandas

**Functions:** analyze_home_visit

**Classes:** 

### `lbw.py`

**Imports:** etl.loader, pandas

**Functions:** analyze_lbw

**Classes:** 

### `loader.py`

**Imports:** os, pandas

**Functions:** load_file, inspect_df

**Classes:** 

### `measuring_efficiency.py`

**Imports:** etl.loader, pandas

**Functions:** analyze_me

**Classes:** 

### `metadata.py`

**Imports:** 

**Functions:** 

**Classes:** 

### `snp.py`

**Imports:** etl.loader, pandas

**Functions:** analyze_snp

**Classes:** 


## 📁 Folder: `etl\__pycache__`

### `adolescent_girls.cpython-313.pyc` (non-python file)

### `anaemia.cpython-313.pyc` (non-python file)

### `awc_summary.cpython-313.pyc` (non-python file)

### `gm_5_6.cpython-313.pyc` (non-python file)

### `gwg.cpython-313.pyc` (non-python file)

### `home_visit.cpython-313.pyc` (non-python file)

### `lbw.cpython-313.pyc` (non-python file)

### `loader.cpython-313.pyc` (non-python file)

### `measuring_efficiency.cpython-313.pyc` (non-python file)

### `snp.cpython-313.pyc` (non-python file)


## 📁 Folder: `models`

### `lbw_model.joblib` (non-python file)

### `stunting_model.joblib` (non-python file)


## 📁 Folder: `plots`

### `correlation_heatmap.png` (non-python file)

### `scatter_Measurement_Efficiency_vs_Stunting_Total_%.png` (non-python file)

### `scatter_PW_Anaemia_Rate_vs_LBW_Rate_%.png` (non-python file)

### `top_bottom_LBW_Rate_pct.png` (non-python file)

### `top_bottom_Stunting_Total_pct.png` (non-python file)


## 📁 Folder: `utils`

### `cleaner.py`

**Imports:** pandas

**Functions:** standardize_columns, normalize_awc_code, fill_missing

**Classes:** 

### `config.py`

**Imports:** pathlib

**Functions:** month_path

**Classes:** 

### `files.py`

**Imports:** pandas, pathlib

**Functions:** load_csv, save_csv, list_month_folders

**Classes:** 

### `logging.py`

**Imports:** logging

**Functions:** 

**Classes:** 

### `models.py`

**Imports:** joblib, pathlib

**Functions:** load_model, save_model

**Classes:** 

### `stats.py`

**Imports:** pandas

**Functions:** safe_corr, top_bottom

**Classes:** 

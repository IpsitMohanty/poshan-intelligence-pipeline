from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CUBES_DIR = ROOT / "cubes"
PLOTS_DIR = ROOT / "plots"
MODELS_DIR = ROOT / "models"

DEFAULT_MONTH = "2025-11"

def month_path(month: str):
    return DATA_DIR / month

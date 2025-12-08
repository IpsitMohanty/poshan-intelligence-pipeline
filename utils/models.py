from pathlib import Path
import joblib

def load_model(path: Path):
    return joblib.load(path)

def save_model(model, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)

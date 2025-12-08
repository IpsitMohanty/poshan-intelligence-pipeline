import pandas as pd
import os   # ← ADD THIS

def load_file(path: str):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(path)
    elif ext in [".xlsx", ".xls"]:
        return pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def inspect_df(df: pd.DataFrame):
    return {
        "rows": len(df),
        "columns": list(df.columns),
        "missing": df.isnull().sum().to_dict(),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "preview": df.head().to_dict()
    }

def load_all_files(folder):
    """
    Load all CSV/XLSX files inside the given month folder.
    Returns a dict: {"filename_without_ext": DataFrame}
    """
    folder = str(folder)
    data = {}

    for fname in os.listdir(folder):
        if fname.lower().endswith((".csv", ".xlsx", ".xls")):
            fpath = os.path.join(folder, fname)
            key = os.path.splitext(fname)[0]  # remove extension
            print(f"[LOADER] Loading {fname} ...")
            data[key] = load_file(fpath)

    print(f"[LOADER] Loaded {len(data)} files from {folder}")
    return data

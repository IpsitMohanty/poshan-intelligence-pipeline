from pathlib import Path
import re

MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")  # YYYY-MM

def get_month_folders(base_dir: Path):
    """
    Return all directories inside base_dir that match YYYY-MM.
    """
    if not base_dir.exists():
        raise FileNotFoundError(f"Base directory not found: {base_dir}")

    return [
        p for p in base_dir.iterdir()
        if p.is_dir() and MONTH_PATTERN.match(p.name)
    ]


def get_latest_month_folder(base_dir: Path) -> Path:
    """
    Detect the latest month folder under base_dir based on lexicographic ordering.
    Example:
        2025-09 < 2025-10 < 2025-11 < 2025-12
    """
    month_folders = get_month_folders(base_dir)

    if not month_folders:
        raise RuntimeError(f"No month folders found under {base_dir}")

    # YYYY-MM auto-sorts correctly as strings.
    latest = max(month_folders, key=lambda p: p.name)
    return latest

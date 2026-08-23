"""Profile genuine source missingness across the 12 real monthly report CSVs.

This must run BEFORE the real data is removed from the working tree (Step 1
of the history-purge plan) or gitignored, because the output of this script
is the only artifact that preserves the "genuine source missingness" signal
once the raw files are gone. The Phase 1 synthetic generator reads this
profile's output (data/missingness_profile.json) to reproduce the same
per-column null/blank rates instead of zero-filling every field.

The real 2025-11 exports carry no blank/NaN cells at all (confirmed: zero
occurrences of an empty field in any of the 13 files). Genuine missingness
here instead shows up as three structural patterns, all captured below:
  - entity-level absence: a district present in the canonical 30-district
    roll call but missing entirely from a given report (e.g. Adolescent
    Girls has only 10 of 30 districts that month - 20 districts simply did
    not submit that report)
  - systematic all-zero columns: a numeric column that is exactly 0 for
    every reporting row while sibling columns in the same file are
    genuinely populated (e.g. Anaemia's "Haemoglobin Measured of Children
    (6 months - 5 years)" is 0 for all 30 districts while the Pregnant
    Women / Lactating Mother haemoglobin columns in the same file have real
    nonzero values) - this is non-collection wearing a zero, not a true
    operational zero, and must NOT be treated as "no missingness" just
    because the cell is non-blank
  - explicit missingness-as-a-column: some reports carry a literal
    "Reference data not found" column (seen verbatim, duplicated, as a
    header in the Growth Monitoring reports) whose value is itself a count
    of rows where reference/growth-standard lookup failed
  - the literal sentinel text ("Reference data not found", "N/A", etc.)
    inside a cell, for reports/months where that does occur

Usage:
    python scripts/profile_missingness.py [--data-dir data/2025-11] [--out data/missingness_profile.json]
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import pandas as pd

SENTINEL_STRINGS = {"reference data not found", "n/a", "na", "null", "-"}

# Aggregate footer rows some of the real exports append (e.g. a trailing
# "Total" row summing all districts). These are not entities and must be
# excluded from the canonical district roll call / entity-coverage math,
# or they masquerade as an extra "district".
FOOTER_ROW_LABELS = {"total", "grand total", "all districts", "state total", "odisha"}


def raw_header_columns(path: Path) -> list:
    """Read just the header line, undeduplicated, to detect literal
    duplicate column names (pandas silently mangles these to `.1`, `.2`,
    ... on read_csv, which would otherwise hide the "Reference data not
    found" x2 pattern)."""
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return next(csv.reader(fh))


def profile_file(path: Path) -> dict:
    # keep_default_na=False + explicit na_values so we can tell "truly blank"
    # apart from a literal "NA"-looking district name, and so sentinel text
    # is inspected rather than silently converted to NaN by pandas.
    df_raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    key_col_raw = df_raw.columns[0]
    footer_mask = df_raw[key_col_raw].str.strip().str.lower().isin(FOOTER_ROW_LABELS)
    footer_rows = sorted(df_raw.loc[footer_mask, key_col_raw].str.strip().unique().tolist())
    df = df_raw.loc[~footer_mask].reset_index(drop=True)
    n_rows = len(df)

    raw_headers = raw_header_columns(path)
    duplicate_headers = sorted(
        {h.strip() for h in raw_headers if h.strip() and raw_headers.count(h) > 1}
    )

    columns = {}
    for col in df.columns:
        series = df[col]
        blank_mask = series.str.strip() == ""
        sentinel_mask = series.str.strip().str.lower().isin(SENTINEL_STRINGS) & ~blank_mask
        n_blank = int(blank_mask.sum())
        n_sentinel = int(sentinel_mask.sum())
        n_present = n_rows - n_blank - n_sentinel

        numeric = pd.to_numeric(series, errors="coerce")
        n_numeric_parseable = int(numeric.notna().sum())
        all_zero_suspect = bool(
            n_numeric_parseable > 0
            and n_numeric_parseable == n_rows
            and (numeric.fillna(-1) == 0).all()
        )

        columns[col] = {
            "n_rows": n_rows,
            "n_present": n_present,
            "n_blank": n_blank,
            "n_sentinel": n_sentinel,
            "blank_rate": round(n_blank / n_rows, 6) if n_rows else 0.0,
            "sentinel_rate": round(n_sentinel / n_rows, 6) if n_rows else 0.0,
            "sentinel_values_seen": sorted(
                {v.strip() for v in series[sentinel_mask].tolist()}
            ),
            "all_zero_suspect": all_zero_suspect,
        }

    # first column of every one of these report types is the district/
    # category key; capture it separately so the generator can align
    # entity-level (structural) presence, not just cell-level blankness.
    key_col = df.columns[0]
    entities_present = sorted(df[key_col].dropna().astype(str).str.strip().unique().tolist())

    return {
        "file": path.name,
        "n_rows": n_rows,
        "n_columns": len(df.columns),
        "columns_in_order": list(df.columns),
        "duplicate_column_headers": duplicate_headers,
        "key_column": key_col,
        "footer_rows_excluded": footer_rows,
        "entities_present": entities_present,
        "column_missingness": columns,
        "all_zero_suspect_columns": [c for c, v in columns.items() if v["all_zero_suspect"]],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/2025-11", help="Directory of real source CSVs to profile.")
    parser.add_argument("--out", default="data/missingness_profile.json", help="Output JSON path.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    data_dir = (repo_root / args.data_dir).resolve()
    out_path = (repo_root / args.out).resolve()

    csv_paths = sorted(data_dir.glob("*.csv"))
    if not csv_paths:
        raise SystemExit(f"No CSVs found in {data_dir}")

    profiles = {}
    for path in csv_paths:
        print(f"Profiling {path.name} ...")
        profiles[path.name] = profile_file(path)

    # Canonical entity roll call = the largest entities_present set among
    # files keyed by district (heuristic: key column name mentions
    # "district" and has >=20 entities). Reports keyed by something else
    # (e.g. Measurement_Efficiency_Status's numeric/lettered category index,
    # SNP_Projections' AWC-level grain) are left out of coverage comparison
    # entirely rather than force-fit against a district roll call.
    district_keyed = [
        p for p in profiles.values()
        if "district" in p["key_column"].lower() and len(p["entities_present"]) >= 20
    ]
    canonical_districts = sorted(max(
        (p["entities_present"] for p in district_keyed), key=len, default=[]
    ))

    for name, p in profiles.items():
        if "district" in p["key_column"].lower() and canonical_districts:
            missing = sorted(set(canonical_districts) - set(p["entities_present"]))
            p["missing_entities_vs_canonical"] = missing
            p["entity_coverage_rate"] = round(
                1 - len(missing) / len(canonical_districts), 4
            ) if canonical_districts else None
        else:
            p["missing_entities_vs_canonical"] = None
            p["entity_coverage_rate"] = None

    summary = {
        "canonical_district_roll_call": canonical_districts,
        "canonical_district_count": len(canonical_districts),
        "source_period": data_dir.name,
        "source_dir": str(data_dir.relative_to(repo_root)),
        "n_files_profiled": len(profiles),
        "note": (
            "Real source missingness profile. Consumed by the Phase 1 synthetic "
            "generator to reproduce genuine blank/sentinel rates per column "
            "instead of zero-filling. Contains no real values, counts, or "
            "identifiers beyond column names, district/entity name lists, and "
            "aggregate missingness rates."
        ),
        "files": profiles,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote missingness profile: {out_path}")
    print(f"Canonical district roll call: {len(canonical_districts)} districts")
    print(f"Files profiled: {len(profiles)}")
    for name, p in profiles.items():
        n_blank_sentinel_cols = sum(
            1 for c in p["column_missingness"].values() if c["n_blank"] or c["n_sentinel"]
        )
        bits = [f"{p['n_rows']} rows", f"{p['n_columns']} cols"]
        if p["footer_rows_excluded"]:
            bits.append(f"footer rows excluded: {p['footer_rows_excluded']}")
        if p["entity_coverage_rate"] is not None:
            bits.append(f"entity coverage: {p['entity_coverage_rate']:.0%}")
            if p["missing_entities_vs_canonical"]:
                bits.append(f"missing entities: {p['missing_entities_vs_canonical']}")
        if p["all_zero_suspect_columns"]:
            bits.append(f"all-zero suspect cols: {p['all_zero_suspect_columns']}")
        if p["duplicate_column_headers"]:
            bits.append(f"duplicate headers: {p['duplicate_column_headers']}")
        if n_blank_sentinel_cols:
            bits.append(f"{n_blank_sentinel_cols} cols with blank/sentinel cells")
        print(f"  {name}: " + " | ".join(bits))


if __name__ == "__main__":
    main()

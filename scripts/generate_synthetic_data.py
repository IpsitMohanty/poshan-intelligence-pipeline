"""Synthetic monthly ICDS/Poshan report generator for poshan-intelligence-pipeline.

Produces fictional data/2025-11/*.csv files matching the real export schema
handled by etl/*.py and cubes/district_cube.py: same 13 filenames, same
column names (including quirks - double spaces, duplicate headers, a
state-level "Total" rollup row), same single-month date-range text baked
into Home Visit's headers. It also injects deliberate anomalies so the
pipeline has something for future data-quality checks to catch, and
reproduces the *structural* missingness found in the real data (see
data/missingness_profile.json) instead of zero-filling every field.

ALL DATA PRODUCED BY THIS SCRIPT IS FICTIONAL. No real district, AWC,
Anganwadi worker, or beneficiary is represented. Every district name below
is procedurally generated and checked against the real Odisha district
list to guarantee no collision.

Design notes / provenance (see also data/missingness_profile.json and
scripts/profile_missingness.py, which this script's --check-profile mode
cross-validates against):

- Single month only. 2025-11 is the only month that has ever existed in
  this repo (git history and disk both confirm it) - this generator does
  not attempt to simulate month-over-month drift the way the sibling
  awc-operations-dashboard generator does across 12 months. That is a
  known, stated limitation: the real pipeline's monthly-format-drift
  handling is untested by this synthetic dataset. See README.

- Adolescent Girls coverage: the real report only ever covered 10 of 30
  districts (etl never zero-fills the other 20 - they are simply absent
  rows). Reproduced here as an entity-level absence, not a blank value:
  exactly 10 of the 30 fictional districts get an Adolescent_Girls row,
  chosen deterministically by the seed. The SNP report's "Adolescent
  Girls" column mirrors this same coverage split (nonzero only for
  AG-covered districts, 0 for the other 20) - a second real cross-file
  consistency this generator reproduces.

- Anaemia's "Haemoglobin Measured of Children (6 months - 5 years)" and
  its "Anaemic" (children) column are systematically 0 for every district
  in the real data while the Pregnant-Women/Lactating-Mother columns in
  the same file are genuinely populated - non-collection wearing a zero,
  not a true operational zero. Reproduced verbatim (literal 0, not a
  sampled near-zero) - this is the honesty-preservation crux: sampling a
  small positive number here would launder a non-collection as a
  measurement.

- Anaemia's triple "Anaemic" column (PW / LM / Child, positionally
  distinguished only by pandas' automatic .1/.2 mangling on read) is
  exercised directly by etl/anaemia.py's rename dict
  ("anaemic" -> anaemic_pw, "anaemic.1" -> anaemic_lm,
  "anaemic.2" -> anaemic_child). This is not cosmetic: get the column
  order or count wrong and that rename silently no-ops, and
  child_anaemia_rate/pw_anaemia_rate/lm_anaemia_rate all break. This
  generator writes the literal duplicate header three times in the same
  positions as the real export.

- Growth Monitoring (0-5 years) carries a state-level "Total" rollup row
  after the 30 districts (etl/gm_0_5.py explicitly drops it - see that
  module's comment and tests/test_pipeline_reconciliation.py's
  referential-integrity tests, which pin the fix). Reproduced here so
  that drop-logic keeps being exercised by real data shape, not silently
  skipped because the synthetic fixture is "too clean". The 0-5 file also
  carries two literal "Reference data not found" columns (also
  duplicate-named) - unlike Anaemia's duplicate, no ETL code reads these
  by name; reproduced anyway for schema fidelity since it costs nothing.

- Home Visit's column headers hardcode the literal one-month date range
  ("Between 01 - 30 Nov, 2025", with a real double-space before "30").
  etl/home_visit.py's rename dict is hardcoded to match this exact
  string. Reproduced verbatim.

Usage:
    python scripts/generate_synthetic_data.py [--output-dir data/2025-11] [--seed 42]
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

N_DISTRICTS = 30
MONTH_LABEL = "2025-11"
SOURCE_MONTH_TAG = "11_2025"  # filename tag used by 11 of the 13 files
SNP_MONTH_TAG = "12_2025"  # SNP's filename uses next-month tag in the real export - reproduced verbatim

REAL_ODISHA_DISTRICTS = {
    "angul", "balangir", "balasore", "bargarh", "bhadrak", "boudh", "cuttack",
    "deogarh", "dhenkanal", "gajapati", "ganjam", "jagatsinghpur", "jajapur",
    "jharsuguda", "kalahandi", "kandhamal", "kendrapara", "keonjhar", "khordha",
    "koraput", "malkangiri", "mayurbhanj", "nabarangpur", "nayagarh", "nuapada",
    "puri", "rayagada", "sambalpur", "subarnapur", "sundergarh",
}

NAME_SYLLABLES = [
    "va", "ki", "ma", "ra", "su", "lo", "ne", "ta", "bi", "cha",
    "de", "go", "ja", "ha", "pu", "sha", "tri", "vi", "ka", "no",
    "ru", "sa", "ma", "pra", "gi", "la", "dho", "mi", "ba", "chi",
]
NAME_SUFFIXES = [
    "pur", "garh", "nagar", "khand", "giri", "pada", "sahi", "bandha", "vana", "kot",
]

# Row-level anomaly rate applied to district-grain report files (mirrors the
# AWC generator's ROW_ANOMALY_RATE convention).
ROW_ANOMALY_RATE = 0.02


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def unique_district_names(rng: random.Random, n: int) -> list:
    names = set()
    out: list = []
    tries = 0
    while len(out) < n:
        tries += 1
        if tries > 10000:
            raise RuntimeError("Could not generate enough unique fictional district names.")
        stem = "".join(rng.sample(NAME_SYLLABLES, k=2))
        name = f"{stem}{rng.choice(NAME_SUFFIXES)}".capitalize()
        key = name.lower()
        if key in names or key in REAL_ODISHA_DISTRICTS:
            continue
        names.add(key)
        out.append(name)
    return out


@dataclass
class District:
    name: str
    # AWC infrastructure (shared across AWC / AWC_Staff / SNP / VHSND files)
    active_awc: int
    inactive_awc: int
    n_projects: int
    n_sectors: int
    # Population bases
    children_0_5: int
    children_5_6: int
    children_0_6m: int
    pregnant_women: int
    lactating_mothers: int
    ag_total: int = 0  # 0 unless this district is in the AG-covered subset
    # Rates (fractions, jittered per-file at row-build time)
    stunt_severe_rate: float = 0.0
    stunt_moderate_rate: float = 0.0
    underwt_severe_rate: float = 0.0
    underwt_moderate_rate: float = 0.0
    sam_rate: float = 0.0
    mam_rate: float = 0.0
    lbw_rate: float = 0.0
    pw_anaemia_rate: float = 0.0
    lm_anaemia_rate: float = 0.0
    ag_anaemia_rate: float = 0.0
    measurement_eff: float = 0.0
    visit_coverage: float = 0.0
    anc_completion: float = 0.0
    gwg_optimum_rate: float = 0.0

    @property
    def total_awc(self) -> int:
        return self.active_awc + self.inactive_awc


def build_districts(rng: random.Random) -> list:
    names = unique_district_names(rng, N_DISTRICTS)
    districts = []
    for name in names:
        active_awc = clamp(round(rng.gauss(2600, 1200)), 700, 5200)
        inactive_awc = clamp(round(active_awc * rng.uniform(0.0002, 0.012)), 0, 25)
        n_sectors = clamp(round(active_awc / rng.uniform(18, 28)), 25, 220)
        n_projects = clamp(round(n_sectors / rng.uniform(7, 13)), 2, 28)

        children_0_5 = clamp(round(active_awc * rng.uniform(35, 100)), 15000, 260000)
        children_5_6 = clamp(round(children_0_5 * rng.uniform(0.12, 0.16)), 2000, 40000)
        children_0_6m = clamp(round(children_0_5 * rng.uniform(0.055, 0.09)), 1200, 18000)
        pregnant_women = clamp(round(active_awc * rng.uniform(1.6, 4.8)), 1800, 23000)
        lactating_mothers = clamp(round(pregnant_women * rng.uniform(0.65, 0.95)), 1200, 18000)

        districts.append(District(
            name=name,
            active_awc=active_awc,
            inactive_awc=inactive_awc,
            n_projects=n_projects,
            n_sectors=n_sectors,
            children_0_5=children_0_5,
            children_5_6=children_5_6,
            children_0_6m=children_0_6m,
            pregnant_women=pregnant_women,
            lactating_mothers=lactating_mothers,
            stunt_severe_rate=rng.uniform(0.05, 0.20),
            stunt_moderate_rate=rng.uniform(0.10, 0.28),
            underwt_severe_rate=rng.uniform(0.01, 0.05),
            underwt_moderate_rate=rng.uniform(0.05, 0.18),
            sam_rate=rng.uniform(0.002, 0.012),
            mam_rate=rng.uniform(0.01, 0.045),
            lbw_rate=rng.uniform(0.06, 0.17),
            pw_anaemia_rate=rng.uniform(0.15, 0.55),
            lm_anaemia_rate=rng.uniform(0.5, 0.85),
            ag_anaemia_rate=rng.uniform(0.15, 0.55),
            measurement_eff=rng.uniform(0.93, 1.0),
            visit_coverage=rng.uniform(0.93, 0.995),
            anc_completion=rng.uniform(0.55, 0.98),
            gwg_optimum_rate=rng.uniform(0.15, 0.65),
        ))
    return districts


def assign_ag_coverage(districts: list, rng: random.Random) -> list:
    """Exactly 10 of 30 districts get Adolescent Girls coverage, matching
    the real report's 10/30 entity-level coverage found in
    data/missingness_profile.json. The other 20 simply never appear in
    Adolescent_Girls_(14_18_Years)_11_2025.csv, and get 0 (not blank) in
    SNP's "Adolescent Girls" column - both structural, not cell-blank,
    missingness."""
    covered = rng.sample(districts, 10)
    for d in covered:
        d.ag_total = clamp(round(d.children_0_5 * rng.uniform(0.28, 0.55)), 5000, 45000)
    return covered


# ---------------------------------------------------------------------
# Anomaly injection
# ---------------------------------------------------------------------
def maybe_flag_anomaly(rng: random.Random, anomaly_log: list, source_file: str, district: str, kind: str):
    anomaly_log.append({
        "period": MONTH_LABEL,
        "source_file": source_file,
        "district": district,
        "anomaly_kind": kind,
    })


def perturb_measured_vs_active(rng, active, measured, source_file, district, anomaly_log):
    """Shared measured/active anomaly family used by every file with a
    "measured out of active" pair (GM 0-5, GM 5-6, Measuring Efficiency,
    Adolescent Girls). Returns the possibly-perturbed measured value."""
    if rng.random() >= ROW_ANOMALY_RATE:
        return measured
    kind = rng.choice(["measured_exceeds_active", "measurement_collapse"])
    if kind == "measured_exceeds_active":
        measured = active + rng.randint(3, 40)
    else:
        measured = round(active * rng.uniform(0.02, 0.25))
    maybe_flag_anomaly(rng, anomaly_log, source_file, district, kind)
    return measured


def perturb_percent(rng, pct, source_file, district, anomaly_log):
    if rng.random() >= ROW_ANOMALY_RATE:
        return pct
    pct = rng.choice([
        round(rng.uniform(101, 145), 2),
        round(rng.uniform(-25, -1), 2),
    ])
    maybe_flag_anomaly(rng, anomaly_log, source_file, district, "percent_out_of_range")
    return pct


def perturb_count_negative(rng, value, source_file, district, anomaly_log, field_name):
    if rng.random() >= ROW_ANOMALY_RATE:
        return value
    maybe_flag_anomaly(rng, anomaly_log, source_file, district, f"negative_{field_name}")
    return -rng.randint(1, max(1, round(value * 0.1) or 1))


def n_pct(n, total):
    return round((n / total) * 100, 2) if total else 0.0


# ---------------------------------------------------------------------
# Per-file row builders
# ---------------------------------------------------------------------
def build_awc_rows(districts):
    rows = []
    for d in districts:
        rows.append({
            "District": d.name,
            "Total AWC": d.total_awc,
            "Total Active AWC": d.active_awc,
            "Total Inactive AWC": d.inactive_awc,
            "Newly Added AWC during Month": 0,
            "Inactive AWC during Month": 0,
        })
    return rows


def build_awc_staff_rows(districts, rng):
    rows = []
    for d in districts:
        aww_extra = clamp(round(d.active_awc * rng.uniform(0.003, 0.015)), 0, 70)
        aww = clamp(d.active_awc - rng.randint(0, max(1, round(d.active_awc * 0.01))), 0, d.active_awc)
        awh = clamp(d.active_awc - rng.randint(0, max(1, round(d.active_awc * 0.02))), 0, d.active_awc)
        rows.append({
            "District": d.name,
            "Total AWC Operational": d.active_awc,
            "AWW": aww,
            "AWW on Additional Charges": aww_extra,
            "AWH": awh,
        })
    return rows


GM_0_5_COLUMNS = [
    "District", "Total Active Children Registered in the AWC for the Month",
    "Total Active Children measured (Height & Weight) for the Month",
    "Measurement efficiency (%)", "Severely stunted (N)", "Severely stunted (%)",
    "Moderately stunted (N)", "Moderately stunted (%)", "Not stunted (N)", "Not stunted (%)",
    "SAM (N)", "SAM (%)", "MAM (N)", "MAM (%)", "Not Wasted (N)", "Not Wasted (%)",
    "Reference data not found", "Severely underweight (N)", "Severely underweight (%)",
    "Moderately underweight (N)", "Moderately underweight (%)", "Not underweight (N)", "Not underweight (%)",
    "Obese (N)", "Obese (%)", "Overweight (N)", "Overweight (%)",
    "Not Overweight (N)", "Not Overweight (%)", "Reference data not found",
]


def build_gm_0_5_rows(districts, rng, anomaly_log):
    fname = "(0_to_5_Years)_Growth_Monitoring_11_2025.csv"
    rows = []
    totals = {c: 0 for c in GM_0_5_COLUMNS if c not in ("District",) and "%" not in c}
    for d in districts:
        active = d.children_0_5
        measured = clamp(round(active * d.measurement_eff), 0, active)
        measured = perturb_measured_vs_active(rng, active, measured, fname, d.name, anomaly_log)
        eff = n_pct(measured, active)

        stunt_sev = round(measured * d.stunt_severe_rate)
        stunt_mod = round(measured * d.stunt_moderate_rate)
        stunt_normal = max(0, measured - stunt_sev - stunt_mod)

        sam = round(measured * d.sam_rate)
        mam = round(measured * d.mam_rate)
        not_wasted = max(0, measured - sam - mam)
        ref_missing = clamp(round(measured * rng.uniform(0.0005, 0.004)), 0, measured)

        uw_sev = round(measured * d.underwt_severe_rate)
        uw_mod = round(measured * d.underwt_moderate_rate)
        uw_normal = max(0, measured - uw_sev - uw_mod)

        obese = round(measured * rng.uniform(0.005, 0.02))
        overweight = round(measured * rng.uniform(0.01, 0.035))
        not_overweight = max(0, measured - obese - overweight)

        row = {
            "District": d.name,
            "Total Active Children Registered in the AWC for the Month": active,
            "Total Active Children measured (Height & Weight) for the Month": measured,
            "Measurement efficiency (%)": eff,
            "Severely stunted (N)": stunt_sev, "Severely stunted (%)": n_pct(stunt_sev, measured),
            "Moderately stunted (N)": stunt_mod, "Moderately stunted (%)": n_pct(stunt_mod, measured),
            "Not stunted (N)": stunt_normal, "Not stunted (%)": n_pct(stunt_normal, measured),
            "SAM (N)": sam, "SAM (%)": n_pct(sam, measured),
            "MAM (N)": mam, "MAM (%)": n_pct(mam, measured),
            "Not Wasted (N)": not_wasted, "Not Wasted (%)": n_pct(not_wasted, measured),
            "Reference data not found": ref_missing,
            "Severely underweight (N)": uw_sev, "Severely underweight (%)": n_pct(uw_sev, measured),
            "Moderately underweight (N)": uw_mod, "Moderately underweight (%)": n_pct(uw_mod, measured),
            "Not underweight (N)": uw_normal, "Not underweight (%)": n_pct(uw_normal, measured),
            "Obese (N)": obese, "Obese (%)": n_pct(obese, measured),
            "Overweight (N)": overweight, "Overweight (%)": n_pct(overweight, measured),
            "Not Overweight (N)": not_overweight, "Not Overweight (%)": n_pct(not_overweight, measured),
        }
        # Second literal "Reference data not found" column (duplicate
        # name). Verified against every real row (incl. the Total row):
        # both instances always hold the exact same value - it's one
        # underlying reference-lookup-failure count surfaced twice by the
        # export template, not two independent counters.
        row["__second_reference_data_not_found__"] = ref_missing
        rows.append(row)
        for c in totals:
            if c == "Reference data not found":
                totals[c] += row[c]
            else:
                totals[c] += row.get(c, 0)

    return rows, totals


def build_gm_5_6_rows(districts, rng, anomaly_log):
    fname = "(5_to_6_Years)_Growth_Monitoring_11_2025.csv"
    rows = []
    for d in districts:
        active = d.children_5_6
        measured = clamp(round(active * clamp(d.measurement_eff + rng.uniform(-0.01, 0.01), 0.85, 1.0)), 0, active)
        measured = perturb_measured_vs_active(rng, active, measured, fname, d.name, anomaly_log)
        eff = n_pct(measured, active)

        stunt_sev = round(measured * clamp(d.stunt_severe_rate + rng.uniform(-0.02, 0.02), 0, 1))
        stunt_mod = round(measured * clamp(d.stunt_moderate_rate + rng.uniform(-0.02, 0.02), 0, 1))
        stunt_normal = max(0, measured - stunt_sev - stunt_mod)

        uw_sev = round(measured * clamp(d.underwt_severe_rate + rng.uniform(-0.01, 0.01), 0, 1))
        uw_mod = round(measured * clamp(d.underwt_moderate_rate + rng.uniform(-0.02, 0.02), 0, 1))
        uw_normal = max(0, measured - uw_sev - uw_mod)

        rows.append({
            "District": d.name,
            "Total Active Children Registered in the AWC for the Month": active,
            "Total Active Children measured (Height & Weight) for the Month": measured,
            "Measurement efficiency (%)": eff,
            "Severely stunted (N)": stunt_sev, "Severely stunted (%)": n_pct(stunt_sev, measured),
            "Moderately stunted (N)": stunt_mod, "Moderately stunted (%)": n_pct(stunt_mod, measured),
            "Not stunted (N)": stunt_normal, "Not stunted (%)": n_pct(stunt_normal, measured),
            "Severely underweight (N)": uw_sev, "Severely underweight (%)": n_pct(uw_sev, measured),
            "Moderately underweight (N)": uw_mod, "Moderately underweight (%)": n_pct(uw_mod, measured),
            "Not underweight (N)": uw_normal, "Not underweight (%)": n_pct(uw_normal, measured),
        })
    return rows


def build_adolescent_girls_rows(districts, rng, anomaly_log):
    fname = "Adolescent_Girls_(14_18_Years)_11_2025.csv"
    rows = []
    for d in districts:
        if d.ag_total <= 0:
            continue  # structural absence - not a district row at all
        active = d.ag_total
        measured = clamp(round(active * rng.uniform(0.4, 0.995)), 0, active)
        measured = perturb_measured_vs_active(rng, active, measured, fname, d.name, anomaly_log)
        pct = n_pct(measured, active)

        sev_thin = round(measured * rng.uniform(0.004, 0.02))
        thin = round(measured * rng.uniform(0.015, 0.06))
        overweight = round(measured * rng.uniform(0.01, 0.06))
        obese = round(measured * rng.uniform(0.005, 0.025))
        normal = max(0, measured - sev_thin - thin - overweight - obese)

        hb_measured = round(measured * rng.uniform(0.15, 0.9))
        anaemic = round(hb_measured * d.ag_anaemia_rate)

        rows.append({
            "District": d.name,
            "Total Active AG": active,
            "Active AG Measured (Height & Weight)": measured,
            "% of AG measured": pct,
            "Severely Thin": sev_thin,
            "Thin": thin,
            "Normal": normal,
            "Overweight": overweight,
            "Obese": obese,
            "Haemoglobin Measured": hb_measured,
            "Anaemic": anaemic,
        })
    return rows


def build_anaemia_rows(districts, rng, anomaly_log):
    fname = "Anaemia_11_2025.csv"
    rows = []
    for d in districts:
        hb_pw = round(d.pregnant_women * rng.uniform(0.01, 0.45))
        anaemic_pw = round(hb_pw * d.pw_anaemia_rate)
        anaemic_pw = perturb_count_negative(rng, anaemic_pw, fname, d.name, anomaly_log, "anaemic_pw")

        hb_lm = round(d.lactating_mothers * rng.uniform(0.005, 0.1))
        anaemic_lm = round(hb_lm * d.lm_anaemia_rate)

        # Non-collection, not a real zero: the real Nov-2025 export never
        # measured/reported haemoglobin or anaemia for the 6mo-5yr child
        # population in this file at all - every district is exactly 0.
        # Sampling a small positive value here would fabricate a
        # measurement that was never taken; see module docstring.
        hb_child = 0
        anaemic_child = 0

        rows.append({
            "District": d.name,
            "Total Pregnant Women": d.pregnant_women,
            "Haemoglobin Measured of PW": hb_pw,
            "Anaemic": anaemic_pw,
            "Total Lactating Mothers": d.lactating_mothers,
            "Haemoglobin Measured of LM": hb_lm,
            "__Anaemic_LM__": anaemic_lm,
            "Total Children (6months - 5 years)": d.children_0_6m + d.children_5_6,  # rough 6mo-5y proxy
            "Haemoglobin Measured of Children (6months - 5 years)": hb_child,
            "__Anaemic_Child__": anaemic_child,
        })
    return rows


def build_gwg_rows(districts, rng):
    rows = []
    for d in districts:
        total_pw = d.pregnant_women
        due1 = total_pw  # real export: 100% of active PW are "due" ANC1 - exact identity
        completed1 = round(due1 * clamp(d.anc_completion + rng.uniform(-0.05, 0.05), 0.3, 1.0))

        due2 = round(completed1 * rng.uniform(0.9, 0.99))
        completed2 = round(due2 * clamp(d.anc_completion * rng.uniform(0.3, 0.9), 0.05, 1.0))
        optimum2 = round(completed2 * d.gwg_optimum_rate)

        due3 = round(completed2 * rng.uniform(0.55, 0.85))
        completed3 = round(due3 * clamp(d.anc_completion * rng.uniform(0.15, 0.45), 0.02, 1.0))
        optimum3 = round(completed3 * d.gwg_optimum_rate)

        due4 = round(completed3 * rng.uniform(0.3, 0.7))
        completed4 = round(due4 * clamp(d.anc_completion * rng.uniform(0.05, 0.2), 0.01, 1.0))
        optimum4 = round(completed4 * d.gwg_optimum_rate)

        optimum_latest = optimum2 + optimum3 + optimum4
        hb_latest = round((completed2 + completed3 + completed4) * rng.uniform(0.7, 1.0) / 3) if (completed2 + completed3 + completed4) else 0
        anaemic_latest = round(hb_latest * d.pw_anaemia_rate)

        rows.append({
            "DISTRICT": d.name,
            "TOTAL ACTIVE  PREGNANT WOMEN": total_pw,
            "NO. OF PW DUE ANC 1": due1,
            "NO. OF PW COMPLETED ANC 1": completed1,
            "NO. OF PW DUE ANC 2": due2,
            "NO. OF PW COMPLETED ANC 2": completed2,
            "NO. OF PW GAINED OPTIMUM WEIGHT IN ANC 2": optimum2,
            "NO. OF PW DUE ANC 3": due3,
            "NO. OF PW COMPLETED ANC 3": completed3,
            "NO. OF PW GAINED OPTIMUM WEIGHT IN ANC 3": optimum3,
            "NO. OF PW DUE ANC 4": due4,
            "NO. OF PW COMPLETED ANC 4": completed4,
            "NO. OF PW GAINED OPTIMUM WEIGHT IN ANC 4": optimum4,
            "TOTAL NO. OF PW GAINED OPTIMUM WEIGHT AS PER LATEST ANC": optimum_latest,
            "TOTAL HAEMOGLOBIN MEASURED AS PER LATEST ANC": hb_latest,
            "TOTAL ANAEMIC AS PER LATEST ANC": anaemic_latest,
        })
    return rows


def build_home_visit_rows(districts, rng, anomaly_log):
    fname = "Home_Visit_11_2025.csv"
    rows = []
    hv_col = "% of visits made Between 01 -  30 Nov, 2025"
    for d in districts:
        total_aww = d.active_awc
        target = round(total_aww * rng.uniform(13, 16))
        visits = clamp(round(target * d.visit_coverage), 0, target)
        pct = n_pct(visits, target)
        pct = perturb_percent(rng, pct, fname, d.name, anomaly_log)
        aww_60 = clamp(round(total_aww * rng.uniform(0.985, 1.01)), 0, round(total_aww * 1.02))

        rows.append({
            "District": d.name,
            "Total AWW Between 01 -  30 Nov, 2025": total_aww,
            "Total targeted visits Between 01 - 30 Nov, 2025": target,
            "Total visits made Between 01 - 30 Nov, 2025": visits,
            hv_col: pct,
            "AWW completed 60% HV Between 01 - 30 Nov, 2025": aww_60,
        })
    return rows


def build_lbw_rows(districts, rng, anomaly_log):
    fname = "Low_Birth_Weight_11_2025.csv"
    rows = []
    for d in districts:
        total = d.children_0_6m
        lbw = round(total * d.lbw_rate)
        lbw = perturb_count_negative(rng, lbw, fname, d.name, anomaly_log, "lbw_children")
        rows.append({
            "District": d.name,
            "Total Children 0-6M": total,
            "Low Birth Weight Children 0-6M": lbw,
        })
    return rows


def build_measuring_efficiency_rows(districts, rng, anomaly_log):
    fname = "Measuring_Efficiency_Children_0_to_6_years_11_2025.csv"
    rows = []
    for d in districts:
        active = d.children_0_5 + d.children_5_6
        measured = clamp(round(active * clamp(d.measurement_eff + rng.uniform(-0.002, 0.002), 0.9, 1.0)), 0, active)
        measured = perturb_measured_vs_active(rng, active, measured, fname, d.name, anomaly_log)
        pct = n_pct(measured, active)
        aww_80 = clamp(d.active_awc - rng.randint(0, max(1, round(d.active_awc * 0.006))), 0, d.active_awc)
        rows.append({
            "District": d.name,
            "Total Active Children": active,
            "Total Active Children Measured": measured,
            "% Children Measured": pct,
            "AWW Completed 80% of ME": aww_80,
        })
    return rows


def build_snp_rows(districts, rng):
    rows = []
    for d in districts:
        c1 = round(d.children_0_5 * rng.uniform(0.42, 0.5))
        c2 = round(d.children_0_5 * rng.uniform(0.38, 0.46))
        c3 = d.children_5_6

        sam1 = round(c1 * d.sam_rate)
        sam2 = round(c2 * d.sam_rate * rng.uniform(0.3, 0.6))
        suw1 = round(c1 * d.underwt_severe_rate * rng.uniform(0.8, 1.3))
        suw2 = round((c2 + c3) * d.underwt_severe_rate * rng.uniform(0.6, 1.1))
        samsuw1 = round(min(sam1, suw1) * rng.uniform(0.15, 0.4))
        samsuw2 = round(min(sam2, suw2) * rng.uniform(0.15, 0.4))

        total_beneficiary = d.pregnant_women + d.lactating_mothers + c1 + c2 + c3

        rows.append({
            "District": d.name,
            "Project": d.n_projects,
            "Sector": d.n_sectors,
            "AWC": d.active_awc,
            "Total Beneficiary": total_beneficiary,
            "Total PW": d.pregnant_women,
            "Total LM": d.lactating_mothers,
            "Total Children (6m to 3yr)": c1,
            "Total Children (3yr to 5yr)": c2,
            "Total Children (5yr to 6yr)": c3,
            "Total SAM children (6m to 3yr)": sam1,
            "Total SAM children (3 yr to 5 yr)": sam2,
            "Total SUW children (6m to 3yr)": suw1,
            "Total SUW children (3yr to 6yr)": suw2,
            "Total SAM with SUW Children (6m-3y)": samsuw1,
            "Total SAM with SUW Children (3y-5y)": samsuw2,
            # Same 10/30 coverage as the Adolescent_Girls report - a
            # non-covered district gets a real 0 here, not the AG total.
            "Adolescent Girls": d.ag_total,
        })
    return rows


def build_vhsnd_rows(districts, rng):
    rows = []
    for d in districts:
        total_awc = d.active_awc
        cbe = round(total_awc * 2 * rng.uniform(0.995, 1.005))
        vhsnd = clamp(round(total_awc * rng.uniform(0.94, 1.0)), 0, total_awc)
        field_func = round(total_awc * rng.uniform(3.6, 5.2))
        participants = round(field_func * rng.uniform(6.5, 11))
        vaccinations = round(participants * rng.uniform(0.18, 0.42))
        rows.append({
            "District": d.name,
            "Total AWC": total_awc,
            "Total CBE": cbe,
            "Total VHSND": vhsnd,
            "Field Functionaries": field_func,
            "Total Participants": participants,
            "Vaccinations": vaccinations,
        })
    return rows


def build_measurement_efficiency_status_rows(gm_0_5_totals: dict, gm_5_6_rows: list, rng):
    """State-level rollup, not district-keyed at all (unlike every other
    report). Derived from the sums of the district-level GM files this
    generator already produced, so it stays internally consistent with
    them - matching the real export, where this row's 2,619,812 total
    equals GM 0-5's own committed Total-row figure exactly."""
    total_0_5 = gm_0_5_totals["Total Active Children Registered in the AWC for the Month"]
    measured_0_5 = gm_0_5_totals["Total Active Children measured (Height & Weight) for the Month"]

    frac_0_6m = rng.uniform(0.070, 0.085)
    frac_3_5 = rng.uniform(0.42, 0.46)
    a = round(total_0_5 * frac_0_6m)
    c = round(total_0_5 * frac_3_5)
    b = total_0_5 - a - c

    measured_a = round(a * rng.uniform(0.994, 0.999))
    measured_c = round(c * rng.uniform(0.994, 0.999))
    measured_b = measured_0_5 - measured_a - measured_c

    total_5_6 = sum(r["Total Active Children Registered in the AWC for the Month"] for r in gm_5_6_rows)
    measured_5_6 = sum(r["Total Active Children measured (Height & Weight) for the Month"] for r in gm_5_6_rows)

    def eff(m, t):
        return round((m / t) * 100, 2) if t else 0.0

    return [
        {"": "1", "CATEGORY": "Children 0-5 Years", "TOTAL ACTIVE CHILDREN": total_0_5,
         "TOTAL ACTIVE CHILDREN MEASURED": measured_0_5, "MEASUREMENT EFFICIENCY (%)": eff(measured_0_5, total_0_5)},
        {"": "a", "CATEGORY": "Children 0-6 Months", "TOTAL ACTIVE CHILDREN": a,
         "TOTAL ACTIVE CHILDREN MEASURED": measured_a, "MEASUREMENT EFFICIENCY (%)": eff(measured_a, a)},
        {"": "b", "CATEGORY": "Children 6 months - 3 Years", "TOTAL ACTIVE CHILDREN": b,
         "TOTAL ACTIVE CHILDREN MEASURED": measured_b, "MEASUREMENT EFFICIENCY (%)": eff(measured_b, b)},
        {"": "c", "CATEGORY": "Children 3-5 Years", "TOTAL ACTIVE CHILDREN": c,
         "TOTAL ACTIVE CHILDREN MEASURED": measured_c, "MEASUREMENT EFFICIENCY (%)": eff(measured_c, c)},
        {"": "2", "CATEGORY": "Children 5-6 Years", "TOTAL ACTIVE CHILDREN": total_5_6,
         "TOTAL ACTIVE CHILDREN MEASURED": measured_5_6, "MEASUREMENT EFFICIENCY (%)": eff(measured_5_6, total_5_6)},
    ]


# ---------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------
def write_csv(rows: list, columns: list, out_path: Path):
    df = pd.DataFrame(rows, columns=columns)
    df.to_csv(out_path, index=False, encoding="utf-8")


def write_gm_0_5(rows, totals, out_path: Path):
    # Build the file text by hand for this one file so the two literal
    # "Reference data not found" columns really are duplicate header text
    # (pandas' DataFrame constructor cannot hold two same-named columns).
    lines = [",".join(GM_0_5_COLUMNS)]
    for r in rows:
        values = [str(r[c]) for c in GM_0_5_COLUMNS[:-1]] + [str(r["__second_reference_data_not_found__"])]
        lines.append(",".join(values))
    # totals dict doesn't carry percentages; recompute footer percentages
    # from footer counts, matching how the real Total row is itself a
    # genuine re-aggregation, not a re-sum-of-percentages.
    measured = totals["Total Active Children measured (Height & Weight) for the Month"]
    active = totals["Total Active Children Registered in the AWC for the Month"]
    footer = {"District": "Total"}
    footer.update(totals)
    footer["Measurement efficiency (%)"] = n_pct(measured, active)
    for n_col, pct_col in [
        ("Severely stunted (N)", "Severely stunted (%)"), ("Moderately stunted (N)", "Moderately stunted (%)"),
        ("Not stunted (N)", "Not stunted (%)"), ("SAM (N)", "SAM (%)"), ("MAM (N)", "MAM (%)"),
        ("Not Wasted (N)", "Not Wasted (%)"), ("Severely underweight (N)", "Severely underweight (%)"),
        ("Moderately underweight (N)", "Moderately underweight (%)"), ("Not underweight (N)", "Not underweight (%)"),
        ("Obese (N)", "Obese (%)"), ("Overweight (N)", "Overweight (%)"), ("Not Overweight (N)", "Not Overweight (%)"),
    ]:
        footer[pct_col] = n_pct(footer.get(n_col, 0), measured)
    footer_line = [
        str(totals["Reference data not found"]) if c == "Reference data not found" else str(footer.get(c, ""))
        for c in GM_0_5_COLUMNS
    ]
    lines.append(",".join(footer_line))
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_anaemia(rows, out_path: Path):
    columns = [
        "District", "Total Pregnant Women", "Haemoglobin Measured of PW", "Anaemic",
        "Total Lactating Mothers", "Haemoglobin Measured of LM", "Anaemic",
        "Total Children (6months - 5 years)", "Haemoglobin Measured of Children (6months - 5 years)", "Anaemic",
    ]
    lines = [",".join(columns)]
    for r in rows:
        vals = [
            r["District"], r["Total Pregnant Women"], r["Haemoglobin Measured of PW"], r["Anaemic"],
            r["Total Lactating Mothers"], r["Haemoglobin Measured of LM"], r["__Anaemic_LM__"],
            r["Total Children (6months - 5 years)"], r["Haemoglobin Measured of Children (6months - 5 years)"],
            r["__Anaemic_Child__"],
        ]
        lines.append(",".join(str(v) for v in vals))
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_measurement_efficiency_status(rows, out_path: Path):
    columns = ["", "CATEGORY", "TOTAL ACTIVE CHILDREN", "TOTAL ACTIVE CHILDREN MEASURED", "MEASUREMENT EFFICIENCY (%)"]
    lines = [",".join(columns)]
    for r in rows:
        lines.append(",".join(str(r[c]) for c in columns))
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_home_visit(rows, out_path: Path):
    import csv
    columns = [
        "District", "Total AWW Between 01 -  30 Nov, 2025", "Total targeted visits Between 01 - 30 Nov, 2025",
        "Total visits made Between 01 - 30 Nov, 2025", "% of visits made Between 01 -  30 Nov, 2025",
        "AWW completed 60% HV Between 01 - 30 Nov, 2025",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(columns)
        for r in rows:
            writer.writerow([r[c] for c in columns])


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=None, help="Directory to write synthetic monthly CSVs into (default: <repo_root>/data/2025-11).")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else repo_root / "data" / "2025-11"
    output_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    districts = build_districts(rng)
    ag_covered = assign_ag_coverage(districts, rng)

    anomaly_log = []

    awc_rows = build_awc_rows(districts)
    write_csv(awc_rows, [
        "District", "Total AWC", "Total Active AWC", "Total Inactive AWC",
        "Newly Added AWC during Month", "Inactive AWC during Month",
    ], output_dir / "AWC_11_2025.csv")

    awc_staff_rows = build_awc_staff_rows(districts, rng)
    write_csv(awc_staff_rows, ["District", "Total AWC Operational", "AWW", "AWW on Additional Charges", "AWH"],
              output_dir / "AWC_Staff_11_2025.csv")

    gm_0_5_rows, gm_0_5_totals = build_gm_0_5_rows(districts, rng, anomaly_log)
    write_gm_0_5(gm_0_5_rows, gm_0_5_totals, output_dir / "(0_to_5_Years)_Growth_Monitoring_11_2025.csv")

    gm_5_6_rows = build_gm_5_6_rows(districts, rng, anomaly_log)
    write_csv(gm_5_6_rows, [
        "District", "Total Active Children Registered in the AWC for the Month",
        "Total Active Children measured (Height & Weight) for the Month", "Measurement efficiency (%)",
        "Severely stunted (N)", "Severely stunted (%)", "Moderately stunted (N)", "Moderately stunted (%)",
        "Not stunted (N)", "Not stunted (%)", "Severely underweight (N)", "Severely underweight (%)",
        "Moderately underweight (N)", "Moderately underweight (%)", "Not underweight (N)", "Not underweight (%)",
    ], output_dir / "(5_to_6_Years)_Growth_Monitoring_11_2025.csv")

    ag_rows = build_adolescent_girls_rows(districts, rng, anomaly_log)
    write_csv(ag_rows, [
        "District", "Total Active AG", "Active AG Measured (Height & Weight)", "% of AG measured",
        "Severely Thin", "Thin", "Normal", "Overweight", "Obese", "Haemoglobin Measured", "Anaemic",
    ], output_dir / "Adolescent_Girls_(14_18_Years)_11_2025.csv")

    anaemia_rows = build_anaemia_rows(districts, rng, anomaly_log)
    write_anaemia(anaemia_rows, output_dir / "Anaemia_11_2025.csv")

    gwg_rows = build_gwg_rows(districts, rng)
    write_csv(gwg_rows, [
        "DISTRICT", "TOTAL ACTIVE  PREGNANT WOMEN", "NO. OF PW DUE ANC 1", "NO. OF PW COMPLETED ANC 1",
        "NO. OF PW DUE ANC 2", "NO. OF PW COMPLETED ANC 2", "NO. OF PW GAINED OPTIMUM WEIGHT IN ANC 2",
        "NO. OF PW DUE ANC 3", "NO. OF PW COMPLETED ANC 3", "NO. OF PW GAINED OPTIMUM WEIGHT IN ANC 3",
        "NO. OF PW DUE ANC 4", "NO. OF PW COMPLETED ANC 4", "NO. OF PW GAINED OPTIMUM WEIGHT IN ANC 4",
        "TOTAL NO. OF PW GAINED OPTIMUM WEIGHT AS PER LATEST ANC", "TOTAL HAEMOGLOBIN MEASURED AS PER LATEST ANC",
        "TOTAL ANAEMIC AS PER LATEST ANC",
    ], output_dir / "Gestational_Weight_Gain_Report_11_2025.csv")

    hv_rows = build_home_visit_rows(districts, rng, anomaly_log)
    write_home_visit(hv_rows, output_dir / "Home_Visit_11_2025.csv")

    lbw_rows = build_lbw_rows(districts, rng, anomaly_log)
    write_csv(lbw_rows, ["District", "Total Children 0-6M", "Low Birth Weight Children 0-6M"],
              output_dir / "Low_Birth_Weight_11_2025.csv")

    me_rows = build_measuring_efficiency_rows(districts, rng, anomaly_log)
    write_csv(me_rows, [
        "District", "Total Active Children", "Total Active Children Measured",
        "% Children Measured", "AWW Completed 80% of ME",
    ], output_dir / "Measuring_Efficiency_Children_0_to_6_years_11_2025.csv")

    snp_rows = build_snp_rows(districts, rng)
    write_csv(snp_rows, [
        "District", "Project", "Sector", "AWC", "Total Beneficiary", "Total PW", "Total LM",
        "Total Children (6m to 3yr)", "Total Children (3yr to 5yr)", "Total Children (5yr to 6yr)",
        "Total SAM children (6m to 3yr)", "Total SAM children (3 yr to 5 yr)",
        "Total SUW children (6m to 3yr)", "Total SUW children (3yr to 6yr)",
        "Total SAM with SUW Children (6m-3y)", "Total SAM with SUW Children (3y-5y)", "Adolescent Girls",
    ], output_dir / "SNP_Projections_12_2025.csv")

    vhsnd_rows = build_vhsnd_rows(districts, rng)
    write_csv(vhsnd_rows, [
        "District", "Total AWC", "Total CBE", "Total VHSND",
        "Field Functionaries", "Total Participants", "Vaccinations",
    ], output_dir / "VHSND_and_CBE_11_2025.csv")

    me_status_rows = build_measurement_efficiency_status_rows(gm_0_5_totals, gm_5_6_rows, rng)
    write_measurement_efficiency_status(me_status_rows, output_dir / "Measurement_Efficiency_Status_11_2025 (1).csv")

    # --- Anomaly log + generation summary ---
    # Written one level up from output_dir, NOT inside it: output_dir (e.g.
    # data/2025-11) is treated as "the raw source folder" wholesale by
    # etl.loader.load_all_files and enumerated file-for-file by
    # tests/test_pipeline_reconciliation.py's os.listdir(DATA_DIR) - a real
    # monthly export would never contain these, so keeping them out keeps
    # that folder an honest stand-in for the real thing.
    meta_dir = output_dir.parent
    meta_dir.mkdir(parents=True, exist_ok=True)

    anomaly_df = pd.DataFrame(anomaly_log, columns=["period", "source_file", "district", "anomaly_kind"])
    anomaly_path = meta_dir / "synthetic_anomaly_log.csv"
    anomaly_df.to_csv(anomaly_path, index=False)

    summary = {
        "generator": "generate_synthetic_data",
        "seed": args.seed,
        "output_dir": str(output_dir),
        "month": MONTH_LABEL,
        "district_count": N_DISTRICTS,
        "ag_covered_districts": sorted(d.name for d in ag_covered),
        "ag_coverage_fraction": round(len(ag_covered) / N_DISTRICTS, 4),
        "row_anomaly_rate_target": ROW_ANOMALY_RATE,
        "row_anomaly_count": len(anomaly_log),
        "files_written": 13,
    }
    (meta_dir / "synthetic_generation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Synthetic dataset written to: {output_dir}")
    print(f"Districts: {N_DISTRICTS} (AG-covered: {len(ag_covered)})")
    print(f"Anomalies injected: {len(anomaly_log)}")
    print(f"Anomaly log: {anomaly_path}")


if __name__ == "__main__":
    main()

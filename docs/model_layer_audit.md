# Model-layer audit: is `predict_lbw`/`predict_stunting` defensible at n=30?

Read-only audit, current history only (no `git filter-repo`, no purge). Numbers below come from two sources: the already-committed `docs/baseline_model_metrics_real_2025-11.json`, and one fresh transient run against the real pre-purge `data/2025-11` (via a `git worktree` at commit `e37ca94`, removed after this audit — nothing here was written back into the committed tree; `data/2025-11` on disk stays synthetic).

## Two facts that bound every option

**Grain check — no larger-sample grain exists, real or synthetic.** Checked every real source file's actual row count at `e37ca94` (before untracking): all 13 files are district-level or coarser — 30 rows (one per district) for ten of them, 10 rows for Adolescent Girls, 5 category rows for Measurement Efficiency Status. `SNP_Projections_12_2025.csv` *looks* like it might carry project/sector/AWC-level rows (it has `Project`, `Sector`, `AWC` columns), but those are **counts** (Angul's row reads `Project=8, Sector=74, AWC=1689` — meaning "8 projects, 74 sectors, 1,689 AWCs under this district"), not row-keys — it's district-level too. The government exports this pipeline ingests are pre-aggregated to district level before they ever reach this repo; there is no centre/block/sector microdata anywhere in the real data, on disk or in history. The synthetic generator (`scripts/generate_synthetic_data.py`) mirrors this exactly — it also only produces one row per district, 30 rows, because it's schema-matching the real district-level exports. **There is no path to a larger sample here without a different data source entirely.** (The sibling `awc-operations-dashboard` project's centre-level generator is a different project with a different real grain — not applicable to this pipeline's actual source reports.)

**Panel check — no, only one month has ever existed.** Full sweep, `git log --all --name-only` across every local and remote branch, for any `data/<month>` or `warehouse/etl/<month>` folder other than `2025-11`, and for any `district_cube_*`/`bi_subset_*` artifact naming a different month: nothing. `2025-11` is the only month this repository has ever contained. District×month panel modeling is not available with what exists; it would require new real months this pipeline has never seen.

Both facts point the same direction: **n=30 (districts), one cross-section, is the ceiling.** Not a modeling-technique problem — a sample-size ceiling no algorithm choice fixes.

## Per-model verdict

### LBW (`predict_lbw` → `lbw_rate_pct`)

| | R² | MAE |
|---|---|---|
| RandomForest (current) | **-0.192** | 0.0270 |
| Mean-predictor baseline | -0.283 | 0.0305 |
| Single-feature linear (`pw_anaemia_rate` alone) | -0.157 | 0.0258 |

All three are negative R² — worse than predicting a constant. The RandomForest edges out the mean baseline but is *beaten* by the single-feature linear model, and all three MAEs sit within noise of each other (0.026–0.031, against a target that itself only ranges roughly 0.05–0.15). There is no signal here to point to.

**Verdict: documented small-sample negative result, not "unvalidated predictive model."** `predict_lbw` fails to beat a mean-predictor baseline at n=30 — recorded as a sample-size limitation, not a modeling failure to be fixed by trying another algorithm. Framing it as "unvalidated" (current README wording) undersells what was actually found: it *was* evaluated, and it *did not work*. That's a result, and it's the honest one.

### Stunting (`predict_stunting` → `stunting_total_pct`)

**Leakage check first, as instructed.** `stunting_total_pct` is computed entirely inside `etl/gm_5_6.py`, from the *(5 to 6 Years) Growth Monitoring* report's own `severely_stunted_pct` + `moderately_stunted_pct` columns. `suw_ratio` is computed entirely inside `etl/snp.py`, from the *SNP Projections* report's `suw_total` (Severely Underweight children) ÷ `children_total` — a different source file, different raw columns, no shared formula. **No literal data-pipeline leakage.** (There is a real, separate reason for caution: both reports are collected by the same AWC network, in the same districts, the same month — a district's general reporting quality could correlate errors/patterns across *all* its indicators, and chronic undernutrition genuinely does tend to produce both stunting and being underweight in the same children. Either of those would make the two variables correlated for reasons that aren't "the model learned something generalizable" — but that's a confounding/sample-size question, not a pipeline leak.)

| | R² | MAE |
|---|---|---|
| RandomForest (current) | 0.883 | 1.387 |
| Mean-predictor baseline | -0.291 | 5.622 |
| Single-feature linear (`suw_ratio` alone) | **0.487** | 3.029 |

Unlike LBW, this one clearly beats both trivial baselines. But look at where the jump happens: `suw_ratio` *alone*, linearly, already explains about half the variance (R²=0.487) — the RandomForest's headline 0.883 is built on top of that one feature carrying 86% of its own reported importance (from the earlier baseline capture), evaluated on a **9-row test set**. R² on 9 points is not a stable estimate — one well- or poorly-placed held-out district can move it substantially in either direction.

**Verdict: reframe as a correlation finding, not a validated predictor — regardless of the (clean) leakage answer.** "Severely-underweight rate is strongly associated with stunting rate across these 30 districts (single-feature R²≈0.49)" is a claim n=30 can actually support. "A model predicts stunting with R²=0.88" is not — not because the number is fabricated, but because n=30/9-test-rows can't distinguish a real generalizable relationship from a well-correlated small sample, and the number is dominated by one feature that a simple correlation statement already captures just as informatively.

## Overall verdict

Matches the hypothesis this audit was framed to test: **the model layer is honest small-sample exploration, not a validated ML capability** — one negative result (LBW) and one real-but-overstated correlation (stunting), both bounded by a 30-district cross-section that no algorithm swap fixes, confirmed to be the actual ceiling (no larger real grain, no panel) rather than an assumption. The pipeline's defensible, n=30-proof story is what it was already documented as: ETL correctness, warehouse reconciliation, referential integrity, and anomaly surveillance — none of which need a large N to be true.

## Proposed README reframe -- v2, revised per review (not applied)

v1 (below the changelog note) flattened both models to one generic "small-sample exploration" label. Correction: LBW's finding is the RF<linear<mean *complexity-penalty ordering itself*, not just "negative R²" -- keep that structure explicit. Stunting's clean leakage check is a positive, stated result, not a parenthetical hedge. Both n=30/21-train/9-test numbers go directly in the README text, not just linked out to this doc.

Replace the current `analytics/` bullet in **Approach**:

> - `analytics/` -- correlation analysis and lightweight prediction (`predict_lbw`, `predict_stunting`) over the cube.

with:

> - `analytics/` -- correlation analysis over the cube, plus two `RandomForestRegressor` fits (`predict_lbw`, `predict_stunting`) kept in place and tested, but reported as findings rather than shipped predictors: LBW as a structured small-sample negative result, stunting as a leakage-checked correlation -- see [Model Layer Findings](#model-layer-findings).

Replace the last **Limitations** bullet (the finding now lives in its own section, so this line is redundant rather than corrected):

> - `predict_lbw` / `predict_stunting` are lightweight `RandomForestRegressor` fits over the district cube, not tuned or validated against a held-out period -- the tests confirm the models fit and predict without crashing, not that their predictions are accurate.

with nothing -- removed, superseded by the new section below (placed after "Synthetic Data Provenance"):

> ## Model Layer Findings
>
> `predict_lbw` and `predict_stunting` fit a `RandomForestRegressor` against a 30-district cross-section (21 train / 9 test rows, `test_size=0.3, random_state=42`) -- the ceiling on this pipeline's real data: every source report is pre-aggregated to district level before export (`SNP_Projections`' `Project`/`Sector`/`AWC` columns are per-district *counts*, not row-level microdata -- confirmed against the real data before it was regenerated as synthetic), and only one month (`2025-11`) has ever existed in this repository's history, so no district×month panel exists either. Both fits are kept in the codebase and covered by tests (`tests/test_models.py`, `tests/test_models_integration.py`) -- the tests confirm they fit and predict without crashing, not that they predict well. What they actually found, evaluated against a mean-predictor baseline and a single-feature linear fit on the same 9-row holdout:
>
> **LBW -- a structured negative result.** R² on the 9-row holdout: mean-predictor baseline -0.283, RandomForest (7 features) -0.192, single-feature linear on `pw_anaemia_rate` alone -0.157. The *ordering* is the finding, not just the sign: added model complexity doesn't buy predictive power here, it costs it -- the RandomForest sits between the trivial baseline and the simpler linear model, beaten by both the model above it in complexity and the one below. Recorded as a sample-size negative result, not cited as a working predictor.
>
> **Stunting -- a leakage-checked correlation, not a validated predictor.** R² on the same 9-row holdout: mean-predictor baseline -0.291, single-feature linear on `suw_ratio` (severely-underweight rate) alone 0.487, full RandomForest (6 features) 0.883. Verified this is not a pipeline data leak: `stunting_total_pct` is computed entirely from the Growth Monitoring (5-6 years) report (`etl/gm_5_6.py`), `suw_ratio` entirely from the SNP Projections report (`etl/snp.py`) -- two independent source files, no shared columns or formula. The correlation itself is real and worth stating plainly: severely-underweight rate is strongly associated with stunting rate across these 30 districts (R²≈0.49, linear, one feature), consistent with both indicators reflecting chronic undernutrition. The RandomForest's higher 0.883 is not treated as a stronger version of that same finding -- at n=30 with a 9-row test set, R² is too unstable to support a validated-predictor claim, independent of how clean the leakage check came back.
>
> Full methodology -- the baseline-comparison code, the leakage-check trace, the full-history grain/panel sweep -- in `docs/model_layer_audit.md`.

And in **Results: data-quality reconciliation**'s intro, the parenthetical `("evaluation" means checking that the merge didn't silently lose or fabricate data -- not an ML metric)` already sets up this distinction well; no change needed there.

---

### v1 (superseded by the revision above; kept for record)

Replace the current `analytics/` bullet in **Approach**:

> - `analytics/` -- correlation analysis and lightweight prediction (`predict_lbw`, `predict_stunting`) over the cube.

with:

> - `analytics/` -- correlation analysis over the cube, plus two exploratory `RandomForestRegressor` fits (`predict_lbw`, `predict_stunting`) kept and tested as documented small-sample findings, not shipped predictors -- see [Model Layer: Small-Sample Findings, Not Predictions](#model-layer-small-sample-findings-not-predictions).

Replace the last **Limitations** bullet:

> - `predict_lbw` / `predict_stunting` are lightweight `RandomForestRegressor` fits over the district cube, not tuned or validated against a held-out period -- the tests confirm the models fit and predict without crashing, not that their predictions are accurate.

with a new section (placed after "Synthetic Data Provenance"):

> ## Model Layer: Small-Sample Findings, Not Predictions
>
> `predict_lbw` and `predict_stunting` fit against a 30-district cross-section -- one row per district, no larger real grain exists in the source reports (confirmed: `SNP_Projections`' `Project`/`Sector`/`AWC` columns are per-district *counts*, not row-level microdata), and only one month (`2025-11`) has ever existed in this repository, so no district×month panel is available either. n=30 (9-row test split) is a hard ceiling on what supervised learning can claim here, not a choice of algorithm.
>
> - **LBW**: negative R² (-0.19), beaten by a single-feature linear fit (-0.16) and barely ahead of a mean-predictor baseline (-0.28). Recorded as a **sample-size negative result** -- evaluated, and it doesn't work at this n. Not cited as a working predictor anywhere.
> - **Stunting**: R²=0.88 looks strong, but a single feature (`suw_ratio`, severely-underweight rate) alone already gets R²=0.49 linearly, and the full result is measured on 9 held-out rows -- too unstable to call validated. Reframed as a **correlation finding**: severely-underweight rate is strongly associated with stunting rate across these districts, consistent with both indicators reflecting chronic undernutrition. Verified this isn't a pipeline data leak -- the two indicators come from separate source reports (`gm_5_6.py` vs `snp.py`) with no shared computation -- but a real sample size, not a leak, is why it still isn't a validated predictor.
>
> Both fits, and this framing, are exercised by `tests/test_models.py` and `tests/test_models_integration.py` -- the tests confirm the models fit and predict without crashing and pin the column-naming seam to `build_district_cube()`'s real output; they do not claim, and were never meant to claim, predictive accuracy. Full working (mean-baseline / single-feature-linear comparisons, the leakage check) in `docs/model_layer_audit.md`.

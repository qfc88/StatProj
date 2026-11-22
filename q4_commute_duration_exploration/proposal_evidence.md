# Proposal evidence for Question 4: commute duration

## Recommended primary question

> For adults making weekday home-based work trips in the United States, how accurately can home-work distance, planned transport mode, departure period, trip direction, and broad residential context predict reported trip duration?

The intended prediction time is **immediately before departure, after the planned mode is known**. This decision makes mode and departure period legitimate candidate predictors. It excludes realised trip miles (`TRPMILES`) because that value describes the journey that occurred.

## Why this question is feasible

- The curated population contains **4,269 trips**, **2,384 people**, and **1,928 households**.
- Duration is available for **4,266 trips**. Its median is **21.0 minutes**, its 90th percentile is **50.0 minutes**, and its maximum is **950 minutes**.
- The survey-weighted median is **25.0 minutes**. The weight effective sample size is approximately **1734**, showing why raw sample size and weighted population estimates should both be reported.
- The strongest eligible numerical relationship with duration is **GCDWORK** (Spearman rho **0.726**, household-cluster bootstrap 95% interval **[0.699, 0.755]**).
- The strongest categorical separation is **MSACAT** (rank eta **0.199**). Rank eta is unsigned and descriptive.

## Data curation plan

1. Start from the trip table and retain adults (`R_AGE >= 18`), weekdays (`TDWKND = 2`), home-based work trips (`TRIPPURP = 1`), and car, public-transport, walking, or cycling modes.
2. Preserve `HOUSEID`, `PERSONID`, and `TDCASEID`. One row is one trip; people and households can contribute multiple trips.
3. Derive direction from `WHYFROM` and `WHYTO`, and derive interpretable departure periods from `STRTTIME`.
4. Treat -1, -7, -8, and -9 as documented special codes, not zeros. Keep genuine zero-minute durations visible and investigate them.
5. Use `WTTRDFIN5D` for weekday population summaries. Present raw counts beside weighted estimates.
6. Select one home-density definition before modelling. Do not put all strongly correlated density measures in the same transparent model.
7. Freeze the raw data and record all filters, recodes, exclusions, joins, and missing-data decisions.

## Proposed tools

- **Exploration:** distributions and quantiles; weighted and unweighted group summaries; Spearman correlation; rank eta; bias-corrected Cramer's V; missingness comparisons; and sensitivity to extreme durations.
- **Baseline:** the training-set median duration, optionally stratified only by planned mode if this is pre-registered.
- **Transparent main model:** Gamma regression with a log link, log-duration regression, or median quantile regression. Choose after residual and zero-value diagnostics.
- **Nonlinear benchmark:** random forest or gradient-boosted trees with constrained tuning.
- **Uncertainty:** household-cluster bootstrap confidence intervals for descriptive statistics and resampling variability for test metrics.

## Validation plan

1. Put every trip from the same `HOUSEID` in the same partition. This also keeps each person together.
2. Reserve the final test set before feature selection. Use household-grouped cross-validation inside the remaining development sample.
3. If the stated use is transfer to a new region, use a Census-division holdout; otherwise use a household holdout and report regional subgroup performance.
4. Fit imputation, transformations, feature selection, and tuning only on training folds.
5. Report MAE and median absolute error in minutes, 90th-percentile absolute error, interval coverage where applicable, and errors by mode, direction, urban/rural status, and duration band.
6. Compare survey-weighted and unweighted performance, with raw test counts for every subgroup.

## Pre-registered sensitivity analyses

- All valid durations versus a clearly labelled analysis through the 99th percentile; do not silently delete extremes.
- Complete-case `GCDWORK` analysis versus a missing-indicator or training-fold imputation strategy.
- All included modes versus car-only trips, because public-transport and active-travel samples are small.
- All home-based work trips versus the stricter home-to-work direction.
- One selected density measure versus reasonable alternatives.
- Weighted versus unweighted estimation and evaluation.
- A model excluding mode if the intended prediction time is before mode selection.

## Defence focus

- **Prediction time:** explain exactly when mode and departure time become known.
- **Leakage:** `TRPMILES` is a realised journey measure and is diagnostic only.
- **Repeated observations:** ordinary random row splitting would leak household/person information.
- **Outcome shape:** duration is right-skewed, contains extreme observations, and may contain valid or erroneous zeros.
- **Survey design:** weights change population summaries but do not create more independent observations.
- **Mode imbalance:** separate transit and active-travel error estimates will be uncertain.
- **Measurement:** reported duration and straight-line distance contain measurement error; `GCDWORK` is not route distance.
- **Scope:** the results are predictive/associational, not the causal effect of mode, rail, density, or any policy.

## Redundancy checks to mention

### Strong categorical overlaps (bias-corrected Cramer's V at least 0.50)

| categorical_1  | categorical_2    | cramers_v_corrected | complete_n | levels_1 | levels_2 |
| -------------- | ---------------- | ------------------- | ---------- | -------- | -------- |
| RAIL           | MSACAT           | 0.979               | 4269.000   | 2.000    | 4.000    |
| trip_direction | departure_period | 0.556               | 4266.000   | 3.000    | 5.000    |

### Strong numerical overlaps (absolute Spearman rho at least 0.70)

| numeric_1 | numeric_2 | spearman_rho | complete_n |
| --------- | --------- | ------------ | ---------- |
| GCDWORK   | TRPMILES  | 0.884        | 3813.000   |
| HBPPOPDN  | HBRESDN   | 0.866        | 4199.000   |
| HBRESDN   | HTRESDN   | 0.843        | 4187.000   |
| HBPPOPDN  | HTRESDN   | 0.814        | 4217.000   |

## Files to use when writing the proposal

- `duration_summary.csv`: sample and outcome facts.
- `variable_profile.csv`: completeness and dominant values.
- `numeric_duration_associations.csv`: numerical relationships and cluster-bootstrap intervals.
- `categorical_duration_associations.csv`: categorical separation in ranked duration.
- `categorical_predictor_cramers_v.csv`: overlap among categorical predictors.
- `numeric_predictor_pairs.csv`: redundant numerical measures.
- `duration_by_*.csv`: group-specific raw and weighted summaries.
- `missingness_associations.csv`: whether missingness is concentrated in observed groups.
- `extreme_value_sensitivity.csv`: effect of the longest durations.
- `distance_duration_by_mode.csv`: whether the core distance-duration relationship differs by mode.

The association tables are screening evidence, not a final predictor-selection algorithm and not inferential proof.

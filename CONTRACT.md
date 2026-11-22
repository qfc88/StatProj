# Team contract: shared file formats

This file fixes the formats that connect the three parts of the modelling work. Each
person can build and test their part on the fake data (fixture) before the real tables
exist. **Change this file only through a dedicated pull request that the whole team
reviews.** The checks in `src/contract.py` implement every rule below. Run them before
handing a file to someone else.

## 1. Who owns what

| Part | Owner | Files only the owner edits | Reads | Writes |
|---|---|---|---|---|
| Data preparation | Galvin | `src/prepare_data.py` | `Data/` (raw NHTS files) | `outputs/modelling/train.csv`, `outputs/modelling/test.csv` |
| Validation and scoring | Anthony | `src/validation.py`, `src/evaluate.py` | modelling tables, predictions | `outputs/validation/folds.csv`, `outputs/evaluation/*.csv` |
| Models | Jovie | `src/models.py` | modelling Train table, folds | `outputs/predictions/predictions.csv` |
| Shared contract | Whole team | `CONTRACT.md`, `src/contract.py`, `src/paths.py`, `src/make_fixture.py` | | |

`outputs/` is not committed to Git. Every file in it is rebuilt by the scripts.

## 2. Data flow

```text
Data/ --prepare_data--> modelling/train.csv, test.csv
                                  |
                      validation --> validation/folds.csv
                                  |
                          models --> predictions/predictions.csv
                                  |
                        evaluate --> evaluation/metrics.csv
```

The fixture has the same structure under `outputs/fixture/`. It is built by
`python -m src.make_fixture`. Fixture IDs start with `FAKE`. **Numbers computed from the
fixture are only for testing code and never go into the report.**

## 3. Study scope (decided before modelling)

The rules follow the EDA notebook `NHTS_2022_commute_duration.ipynb`:

- Adults with `R_AGE >= 18`, Monday to Friday by calendar day (`TRAVDAY` `02` to `06`),
  home-based work trips (`TRIPPURP == "01"`).
- The household Train/Test split is made on these 4,393 trips **before** narrowing the
  mode scope or removing missing targets. It uses the sorted unique `HOUSEID` values and
  `pandas.Series.sample(frac=0.8, random_state=42)`.
- Main modelling scope: the four mode groups in the proposal. Trips in `other` stay in the
  tables with `in_main_scope = False` so they can be traced.

Expected counts from the EDA, which `prepare_data` must reproduce from the raw data:

| Quantity | Expected |
|---|---:|
| Trips in the EDA sample | 4,393 |
| Train trips / Test trips | 3,516 / 877 |
| Households in both Train and Test | 0 |
| Train households | 1,554 |
| Train rows used for modelling (`in_main_scope` and observed duration) | 3,484 |
| `contract.train_household_fingerprint(train["HOUSEID"])` | `21cddffc9cfa109e97973155efd0100038c68d0d2b41f95eb3760f221fccc23f` |

The fingerprint confirms that the split matches the EDA household by household, not only
in total counts.

**If a count differs, stop and report the difference. Do not change a rule only to match
a number.**

## 4. Modelling tables: `train.csv` and `test.csv`

One row per trip (`TDCASEID`). Each file contains all trips of its partition, including
`other` modes and missing durations. Use `contract.load_modelling_table()` to get the rows
used for modelling. It keeps `in_main_scope == True` and an observed `duration_min`.

| Column | Type | Allowed values / rule | Source |
|---|---|---|---|
| `TDCASEID` | text | Unique, keep leading zeros | Trip |
| `HOUSEID` | text | Household; used for folds | Trip |
| `PERSONID` | text | Person within household, e.g. `02` | Trip |
| `duration_min` | number | Minutes, 0 allowed; empty if `TRVLCMIN = -9` | Trip `TRVLCMIN` |
| `distance_miles` | number | 0 or more; empty unless `distance_status = recorded` | Person `GCDWORK`, joined on `HOUSEID` + `PERSONID` |
| `distance_status` | text | `recorded`, `appropriate_skip` (`-1`), `not_ascertained` (`-9`) | Person `GCDWORK` |
| `trptrans_code` | text | Original two-digit code | Trip `TRPTRANS` |
| `mode_group` | text | `car_van_suv_pickup` (01-04), `public_transit` (08, 10, 11, 12), `walk` (20), `bike` (18), `other` (07, 16, 17, 21) | Trip `TRPTRANS` |
| `in_main_scope` | True/False | True unless `mode_group = other` | derived |
| `departure_minute` | integer | 0-1439; minutes after midnight from HHMM | Trip `STRTTIME` |
| `direction` | text | `home_to_work` (`WHYFROM` 01/02 to `WHYTO` 03/04/05), `work_to_home` (the reverse) | Trip `WHYFROM`, `WHYTO` |
| `residential_context` | text | `urban` (01), `rural` (02) | Trip `URBRUR` |
| `trip_weight` | number | Greater than 0 | Trip `WTTRDFIN5D` |

- **Target:** `duration_min`.
- **Predictors:** `distance_miles`, `distance_status`, `mode_group`, `departure_minute`,
  `direction`, `residential_context`.
- **Not predictors:** IDs, `trptrans_code`, `in_main_scope`, `trip_weight`. `TRPMILES`
  and any other value known only after the trip must not appear in these tables.
- Imputation, encoding and scaling are learned inside each training fold (models part),
  never in `prepare_data`.

## 5. Folds: `folds.csv`

| Column | Type | Rule |
|---|---|---|
| `TDCASEID` | text | Exactly the modelling Train rows, each once |
| `HOUSEID` | text | Same as in the Train table |
| `fold` | integer | 1 to 5 |

All trips of a household are in the same fold. Folds are built from Train only.

## 6. Predictions: `predictions.csv`

| Column | Type | Rule |
|---|---|---|
| `TDCASEID` | text | Every trip in `folds.csv` |
| `fold` | integer | The fold in which the trip was held out |
| `model` | text | Short name, e.g. `baseline_median`, `median_regression` |
| `prediction_min` | number | Predicted minutes, not empty |

Exactly one row per (`TDCASEID`, `model`). Each prediction comes from a model fitted
without the trip's own fold (out-of-fold).

## 7. Metrics (fixed before any results are seen)

All in minutes, computed on out-of-fold predictions for the same trips for every model:

- **Primary:** mean absolute error (MAE), unweighted, over all trips.
- Also: median absolute error and 90th-percentile absolute error.
- Each metric also weighted by `trip_weight`. A weighted quantile is the smallest absolute
  error whose cumulative weight reaches at least the chosen share of the total weight
  (the rule used for the weighted median in the EDA).
- Results by `mode_group` and `residential_context` always show the number of trips.

The Test table is used **once**, after the team has written down the chosen model,
configuration and preprocessing. Test results must not be used to choose a model,
predictor, hyperparameter or fallback.

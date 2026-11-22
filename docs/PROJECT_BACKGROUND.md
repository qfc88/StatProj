# Project background for beginners

## The data

The **2022 NextGen National Household Travel Survey (NHTS)** is run by the US Federal
Highway Administration. Households were asked to report every trip each member made on one
assigned day. The public files in `Data/` are tables:

| File | One row is… | We use it for |
|---|---|---|
| `tripv2pub.csv` | one trip | almost everything (duration, mode, time, purpose) |
| `perv2pub.csv` | one person | home–work distance `GCDWORK` |
| `hhv2pub.csv`, `vehv2pub.csv`, `ldtv2pub.csv` | household / vehicle / long trip | header checks only |
| `NHTS_2022_Codebook_V2.1.xlsx` | variable definitions and codes | looking up what a code means |

Codes are stored as text with leading zeros: `"02"` is not the same as `2`. Special
negative codes mean "missing": `-9` = not ascertained, `-1` = appropriate skip (the
question did not apply). They are not real values.

## What the EDA found (already done)

EDA (exploratory data analysis) means looking carefully at the data before modelling.
The finished notebook `NHTS_2022_commute_duration.ipynb` decided:

- **Who is in the study:** adults (18+), trips Monday to Friday, trips between home and a
  work activity (code `TRIPPURP = 01`): **4,393 trips** by 2,415 people in 1,943 households.
- **Fair testing:** households were split 80% / 20% into **Train** (3,516 trips) and
  **Test** (877 trips). The Test part is locked until the very end.
- **Duration:** in Train, the median trip is **20 minutes**; most trips are short and a few
  are very long. People often report round numbers (15, 30 minutes).
- **Mode:** most trips are by car. Bus/rail, walking and cycling have few trips, so their
  results must always be shown with the number of trips.
- **Distance:** about 1 in 10 trips has no recorded home–work distance (codes `-1` or `-9`).
  These trips are kept, and the missing status is recorded separately.

## What happens now

We compare **prediction methods** against a simple **baseline**: "always guess the median".
If a method cannot beat that, it is not useful. The methods (from the proposal):

| Method | Plain meaning | Role |
|---|---|---|
| Training median (baseline) | Always predict the typical trip length | The bar to beat |
| Median (quantile) regression | A formula that predicts the typical minutes for trips like this one | Main, easy to explain |
| Tree model (gradient boosting, median objective) | Many small yes/no rules combined | Checks if more flexible patterns help |
| Gamma regression (log link) | A formula for the average minutes, suited to positive, skewed values | Alternative from the proposal |

## Glossary

| Term | Meaning | Example in this project |
|---|---|---|
| Trip / record | One row of the Trip table | Home → work at 07:30, 25 minutes |
| Household | People living at the same address (`HOUSEID`) | Two workers in one house give several trips |
| Target | The value we predict | `duration_min` |
| Predictor (feature) | Information used to predict | distance, mode, departure time, direction, urban/rural |
| Median | Middle value after sorting | Durations 10, 20, 90 → median 20 |
| Train / Test | Data to learn from / data kept aside for the final check | 3,516 / 877 trips |
| Fold | One of 5 groups of Train households; each is held out once for scoring | Fold 3 = scored while folds 1, 2, 4, 5 are used to learn |
| Cross-validation | Learn on 4 folds, score on the 5th, repeat 5 times | Gives every Train trip one honest prediction |
| Out-of-fold prediction | A prediction made by a model that never saw that trip's household | What we score |
| Leakage | Using information not available before the trip | `TRPMILES` (distance actually travelled) is forbidden |
| MAE | Mean absolute error: average of the minutes we are off by | Off by 5, 0, 5 → MAE 3.33 minutes |
| Survey weight | How many real US trips one survey trip represents | `trip_weight` (`WTTRDFIN5D`) |
| Imputation | Filling missing values with a rule learned from data | Must be learned inside each fold |
| Fixture | Small fake data with the right format, for testing code | `outputs/fixture/` — never in the report |

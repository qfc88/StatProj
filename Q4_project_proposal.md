# Project proposal: Predicting weekday commute duration with the 2022 NHTS

**Team members:** [Full name — Student ID]; [Full name — Student ID]; [Full name — Student ID]

**Division of responsibilities:** [Name]—data curation and reproducibility; [Name]—modelling and validation; [Name]—interpretation and presentation. All members will review the question, code, results, and final defence.

---

## Primary question and importance

For metropolitan planning organisations and travel-behaviour researchers, can home–work
distance, transport mode, departure period, trip direction, and broad residential context
predict weekday commute trip duration for adults making home-based work trips in the
United States?

Commute duration is a practical measure of access to employment and transport-system
performance. A transparent predictive model can help planners identify which trip and
residential characteristics contain useful information about journey time, and whether
predictions remain reliable across traveller groups and regions. The study makes
predictive and associational claims only; it will not claim that changing mode, rail
access, or residential density causes a change in commute time.

## Data, audience, and unit of observation

**Audience:** Metropolitan planning organisations, public-transport and accessibility
analysts, and travel-behaviour researchers.

**Source:** FHWA 2022 NextGen National Household Travel Survey V2.1 public-use CSV
files, available at [https://nhts.ornl.gov/downloads](https://nhts.ornl.gov/downloads)
(documentation: [https://nhts.ornl.gov/documentation](https://nhts.ornl.gov/documentation);
data accessed April 2025; no redistribution restrictions).

**Accessibility evidence:** The required CSV files have been downloaded and verified
locally: row counts and survey-weighted totals match the values published in the official
NHTS User's Guide, and all cross-table identifiers are intact.

**Unit:** One trip. The analysis population retains adults aged 18 or older making
weekday home-based work trips by car, public transport, walking, or cycling.

**Outcome:** Reported trip duration in minutes (`TRVLCMIN`). Preliminary sample:
approximately **4,269 trips from 2,384 people in 1,928 households**, with valid duration
observed for 4,266 trips. Weekday survey weights (`WTTRDFIN5D`) will be used for
population summaries alongside raw sample counts.

## Candidate methods and validation

**Baseline:** Training-set median — no features, no tuning.

**Candidate methods:** (1) median (quantile) regression as the main transparent model;
(2) Gamma regression with a log link as a parametric alternative for positive durations;
(3) a tuned random forest or gradient-boosted-tree ensemble as a nonlinear benchmark.
Realised trip miles (`TRPMILES`) will be excluded from all prediction pipelines because
it is observed only after travel; it will be used solely as a leakage diagnostic.
`TRPTRANS` records realised mode after the trip; for habitual commuters mode is
typically fixed before departure, so it is treated as a pre-departure predictor and
this assumption is noted as a limitation.

**Validation:** All trips from the same household remain in the same partition. A 20%
household-grouped test set is reserved before feature selection or tuning; the remaining
80% uses household-grouped cross-validation. Evaluation reports MAE, median absolute
error, and 90th-percentile absolute error — unweighted and survey-weighted — broken
down by mode and urban/rural status.

## Main risk and fallback

The largest risk is sparse non-car travel: the sample contains 4,062 car trips but only
130 active-travel trips (walking 99, cycling 31) and 77 public-transport trips. Duration
is strongly right-skewed and reaches 950 minutes; home–work distance is missing for
approximately 10.7% of trips. The fallback is to use robust median regression, combine
walking and cycling as a single active-travel category, report non-car results
descriptively with uncertainty, and, if subgroup validation is unstable, narrow the
confirmatory model to car trips while retaining the broader sample as a clearly labelled
exploratory analysis.

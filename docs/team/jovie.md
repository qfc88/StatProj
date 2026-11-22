# Jovie — prediction methods

**Your part in one sentence:** write the methods that predict how many minutes a trip
takes, and produce one honest (out-of-fold) prediction per trip and method, in the format
of `CONTRACT.md`, section 6.

**Why it matters:** these predictions answer the research question: do the predictors help
compared with always guessing the median?

## You own

`src/models.py` (function `predict_out_of_fold()`).

## Already done for you

- `python -m src.make_fixture` creates fake Train data **and fake folds**, so you can start
  now. Run your script with `python -m src.models --fixture`.
- `contract.load_modelling_table()` gives the rows to model; `contract.PREDICTORS` lists the
  predictors; `contract.check_predictions()` checks your output.

## Steps (one at a time, with your AI assistant)

1. **Baseline (required).** For each fold: take the median `duration_min` of the other four
   folds, predict it for every trip in the held-out fold. Model name `baseline_median`.
   Explain one example: learned median, prediction, actual duration.
2. **Median regression (required, main method).** Quantile 0.5 regression with the six
   predictors. Inside each fold, learn the missing-distance filling, the encoding of
   categories and any scaling from the training folds only (use a scikit-learn `Pipeline`).
   Keep `distance_status` as its own predictor. Decide and explain how departure time is
   represented.
3. **Tree model (benchmark).** For example `HistGradientBoostingRegressor(loss="quantile",
   quantile=0.5)`. If you try several settings, choose them using households inside the
   training folds only; the held-out fold is only for scoring.
4. **Gamma regression (proposal).** Log link. It predicts the conditional **mean**, not the
   median; say so. Fit it on positive durations only and record how many 0-minute rows were
   left out of each fit, but still predict every trip in the held-out fold.
5. **Write and check:** `python -m src.models --fixture`, then on real data once Galvin's
   tables and Anthony's folds exist. `python -m pytest` must pass.
6. **Pull request** with the command, 5 trips showing actual and predictions for each
   method, and a short explanation of the difference between baseline, median regression
   and Gamma.

Never use the Test table. Never use `TRPMILES` or other after-trip information.

## Check your understanding (defence questions)

- The baseline gives the same number to every trip in a fold. What does your model use to
  give a different prediction to one specific trip?
- Why must missing-value filling be learned inside each fold?
- Why can Gamma regression not be fitted on trips with 0 minutes, and what did you do?
- What is the difference between predicting a median and predicting a mean here?

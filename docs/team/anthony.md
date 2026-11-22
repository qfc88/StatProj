# Anthony — validation, scoring and final check

**Your part in one sentence:** make the testing fair (folds by household), score every
method with the same fixed metrics, and run the single final check on Test.

**Why it matters:** a method can look good only because it was scored on households it
had already seen. Your checks make the comparison honest.

## You own

`src/validation.py` (`make_folds()`) and `src/evaluate.py` (`score()`).

## Already done for you

- `python -m src.make_fixture` creates fake Train data and **fake predictions** from two
  fake models, so you can build and test both scripts now
  (`python -m src.validation --fixture`, `python -m src.evaluate --fixture`).
- `contract.check_folds()` and `contract.check_predictions()` check the formats.
- The metrics are fixed in `CONTRACT.md`, section 7 (primary: unweighted MAE).

## Steps (one at a time, with your AI assistant)

1. **Hand check first.** Write a small test: actual `[10, 20, 30]`, prediction
   `[15, 20, 25]` → absolute errors `[5, 0, 5]`, MAE `10/3` minutes. Add a weighted example
   you can compute by hand.
2. **Folds.** Split the modelling Train rows into 5 folds by `HOUSEID` (for example
   scikit-learn `GroupKFold`). Print trips and households per fold and confirm 0 households
   shared between learning and scoring. Hand `folds.csv` to Galvin.
3. **Metrics.** MAE, median absolute error, 90th-percentile absolute error, each unweighted
   and weighted by `trip_weight` (weighted quantile rule in `CONTRACT.md`). Overall, and by
   `mode_group` and `residential_context`, always with the number of trips. Also show how
   much MAE varies across folds.
4. **Compare.** Join predictions to the Train table on `TDCASEID`, confirm every method is
   scored on the same trips, and make the comparison table and one figure (minutes).
5. **Before Test:** the team writes down the chosen model, settings and preprocessing (for
   example in the pull request). Only then fit on all modelling Train rows and score Test
   **once** for the baseline and the chosen model. Mention that historical notebooks
   explored the full sample earlier.
6. **Integration:** run the full order in `README.md` from a fresh clone and fix the
   instructions if anything is unclear.

Report results honestly, including when a method does not beat the baseline.

## Check your understanding (defence questions)

- What is a fold, and why are folds made by household?
- This MAE is computed on how many trips, and where was each prediction made?
- Why is the primary metric chosen before seeing results?
- Why is Test used only once, and what would go wrong if we used it to pick the model?
- How do you read a weighted MAE next to an unweighted one?

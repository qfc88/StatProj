# Team

| Name | Part | Owns | Reviews the pull requests of | Guide |
|---|---|---|---|---|
| Galvin | Data preparation | `src/prepare_data.py` | Anthony | `galvin.md` |
| Jovie | Models | `src/models.py` | Galvin | `jovie.md` |
| Anthony | Validation, scoring, final Test check, integration | `src/validation.py`, `src/evaluate.py` | Jovie | `anthony.md` |
| EDA author (team lead) | Completed EDA notebook; reviews contract changes | `NHTS_2022_commute_duration.ipynb`, `CONTRACT.md` | all | — |

Names are the nicknames used in the team. Tell your AI assistant your nickname at the
start of a session.

## How the parts connect

```text
Galvin   Data/  ──►  outputs/modelling/train.csv, test.csv
Anthony  train.csv ──► outputs/validation/folds.csv
Jovie    train.csv + folds.csv ──► outputs/predictions/predictions.csv
Anthony  predictions.csv ──► outputs/evaluation/metrics.csv  (then Test, once, at the end)
```

Everyone can start immediately on fake data: `python -m src.make_fixture`, then use
`--fixture` with your script.

## Milestones

| Milestone | Done when |
|---|---|
| M1 Code runs on fake data | All four scripts run with `--fixture` (or on raw data for Galvin) and `python -m pytest` passes |
| M2 Real tables | Galvin's tables pass the checks and reproduce the counts and fingerprint in `CONTRACT.md` |
| M3 First comparison | Baseline vs median regression scored on the real folds, in minutes |
| M4 Model chosen | All methods scored; the team writes down the chosen model **before** Test |
| M5 Final answer | Test scored once; table, figure and one failure case ready for the report |

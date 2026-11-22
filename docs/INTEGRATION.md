# Integration: how the parts are joined

Each part is built and tested alone on fake data first. "Integration" is the moment
real outputs from one person become the inputs of the next. `python -m src.status` shows
what is pending at any time.

## Important: outputs are local

`outputs/` is **not** on GitHub. Code is shared; data tables are rebuilt by each person
on their own computer. After a teammate's pull request is merged, you `git pull` and run
their script to get their output.

## Hand-offs

| # | When | Who acts | What they run | Who is unblocked | Message to the team |
|---|---|---|---|---|---|
| H1 | Jovie's PR merged | Anthony, Galvin | `git pull` → `python -m src.prepare_data` | Anthony (real folds) | "prepare_data merged: Train 3,516 / Test 877 / 3,484 modelling rows, fingerprint OK" |
| H2 | Anthony's folds PR merged | Galvin | `git pull` → `python -m src.prepare_data` → `python -m src.validation` | Galvin (real predictions) | "validation merged: 5 folds, 0 shared households" |
| H3 | Galvin's models PR merged | Anthony | `git pull` → steps above → `python -m src.models` | Anthony (scoring) | "models merged: baseline_median, median_regression, …" |
| H4 | Scoring PR merged | Whole team | full run order in `README.md` | Model choice | "First comparison: MAE baseline X min vs model Y min (n = …)" |
| H5 | Model chosen and written down | Anthony | Test scored once | Report | Final table, figure and one failure case |

## Before each hand-off, the author checks

- `python -m pytest` passes and `python -m src.status` shows no `PROBLEM`.
- The PR description contains the real output (counts, metrics) and the exact commands.
- The contract check for your output passes (`src/contract.py`).

## If something does not fit

- A format problem (missing column, wrong code): fix in the owner's file, new commit.
- A contract problem (the format itself must change): separate PR to `CONTRACT.md` and
  `src/contract.py`, reviewed by the whole team, and everyone updates their code.
- A count differs from `CONTRACT.md`: stop, report both numbers; do not change rules to
  match.

## Checklist before Test (milestone M4)

- [ ] All methods scored on the same out-of-fold trips, with trip counts per group.
- [ ] The chosen model, settings and preprocessing are written in a PR or in `docs/`.
- [ ] The team agrees in writing. Only then Anthony scores Test, once.

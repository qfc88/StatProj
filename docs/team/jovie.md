# Jovie — data preparation

**Your part in one sentence:** turn the raw survey files into two clean tables (Train and
Test) where each row is one trip with the target and the predictors, in the format of
`CONTRACT.md`, section 4.

**Why it matters:** Galvin and Anthony use your tables. If a filter or the split is
different from the EDA, every later result is about a different sample.

## You own

`src/prepare_data.py` (function `build_modelling_tables()`).

## Already done for you

- The EDA notebook decided every rule. Read these sections (search the titles):
  "Study sample construction", "# Split the study sample by household",
  "Variable Decisions and Preprocessing".
- `src/contract.py` checks your output; `CONTRACT.md` lists every column and code.
- Expected results: 4,393 trips → Train 3,516 / Test 877 → 3,484 modelling Train rows,
  and the Train-household fingerprint in `CONTRACT.md`, section 3.

## Steps (ask your AI assistant to guide you through one at a time)

1. **Read the raw Trip table** with all codes as text. Look at 5 rows and say what
   `TDCASEID`, `HOUSEID`, `TRVLCMIN` and `TRPTRANS` mean (Codebook, sheet `Trip`).
2. **Apply the study filters** (age 18+, `TRAVDAY` 02–06, `TRIPPURP` 01). Print the count
   after each filter. Expected end: 4,393.
3. **Split by household** exactly as in the notebook: sorted unique `HOUSEID`, then
   `pandas.Series.sample(frac=0.8, random_state=42)`. Check 3,516 / 877 trips, 0 shared
   households, and `contract.train_household_fingerprint(...)` equal to the expected value.
4. **Join home–work distance** from the Person table on `HOUSEID` + `PERSONID`
   (`validate="many_to_one"`). The number of Trip rows must not change.
5. **Recode** each column as in `CONTRACT.md`: duration (`-9` → empty, keep 0), distance and
   its status (`-1`, `-9`), mode group, departure time in minutes after midnight, direction,
   urban/rural, weight.
6. **Write and check:** `python -m src.prepare_data`, then `python -m pytest`. Print a table
   of counts after each step and 5 example rows.
7. **Pull request** with: the command, the counts table, and one example row explained in
   Vietnamese (for example a trip with `distance_status = appropriate_skip` and why it is kept).

If any count or the fingerprint differs: **stop**, write down both numbers, and ask the team.

## Check your understanding (defence questions)

- Why do we split by household and not by trip?
- Why is the split made before removing other modes and missing durations?
- A trip has `GCDWORK = -1`. What does it mean, and why do we keep the trip?
- Why is `TRPMILES` not allowed as a predictor?
- What would change in the results if the seed or the filter were different?

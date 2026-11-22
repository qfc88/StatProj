# Changes from the proposal

The proposal (`Q4_project_proposal.md`) is kept as submitted. This file records where the
completed EDA refined it, so the report and the defence can explain each change. Numbers
come from the EDA notebook `NHTS_2022_commute_duration.ipynb`.

| Topic | Proposal | After the EDA | Why |
|---|---|---|---|
| Weekday definition | "weekday" trips | Monday–Friday by calendar day (`TRAVDAY` 02–06), including Friday evening | The survey's own weekday code (`TDWKND`) counts Friday trips starting at 18:00 or later as weekend (2022 NHTS Derived Variables, pp. 14–15). The team chose the calendar definition. |
| Sample size | about 4,269 trips, 2,384 people, 1,928 households | 4,393 trips, 2,415 people, 1,943 households (before the mode scope) | Follows from the calendar weekday definition. The proposal figures were preliminary. |
| Mode scope | car, public transport, walking, cycling | Main model: the four proposal groups (`car_van_suv_pickup`, `public_transit`, `walk`, `bike`). 39 trips in other modes are kept with `in_main_scope = False` for tracing. | Keeps the proposal scope without silently dropping records. |
| Split | 20% of households for Test, cross-validation on the rest | Households sorted, 80% sampled with seed 42 → Train 3,516 trips (1,554 households), Test 877 trips; split made before the mode scope and missing targets are applied. 5 folds by household inside Train. | Makes the split exactly reproducible. |
| Missing distance | about 10.7% of trips | 474 of 4,393 trips (10.79%): 136 with `-1` (appropriate skip), 338 with `-9` (not ascertained). Kept, with a separate status variable. | The exact rule for `-1` vs `-9` is not stated in the documents checked. |
| Weights | `WTTRDFIN5D` for population summaries | Unchanged. All 3,513 Train trips with observed duration have a positive weight, including 74 Friday-evening trips. Whether the five-day weight is intended for Friday evenings remains open. | Disclosed as a limitation. |
| Methods, metrics | baseline median; median regression; Gamma (log link); tree ensemble; MAE, median and 90th-percentile absolute error, unweighted and weighted, by mode and urban/rural | Unchanged. Primary metric fixed as unweighted MAE (`CONTRACT.md`, section 7). | Fixed before results are seen. |

**Disclosure.** Earlier, historical notebooks explored the full sample before the split.
The final Test evaluation must mention this.

**Do we rewrite the proposal?** No, unless the instructor asks for a revised version. The
proposal is the submitted starting point (instructor approval has not been recorded in
this repository); the report's data-curation and methods sections
explain these refinements, using this table.

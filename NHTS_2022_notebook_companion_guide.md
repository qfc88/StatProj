# NHTS 2022 Notebook Companion Guide

This guide explains what `NHTS_2022_data_exploration.ipynb` does, why each step matters, what the results mean, and what to do before statistical modelling. It is written for a researcher who is new to the National Household Travel Survey.

The main conclusion is that the data files are structurally sound and the proposed weekday commute sample can be created. Car trips dominate the sample. Public transport, walking, and especially cycling have much smaller samples, so the eventual model must remain simple. Two notebook corrections are needed: unique people must be counted with `HOUSEID + PERSONID`, and the saved Jupyter kernel name should be changed from `base` to the installed `python3` kernel.

# The research idea

The future research question is:

> Among a clearly defined class of U.S. trips, how are traveller, household, trip, and accessibility characteristics associated with choosing car, public transport, walking, or cycling?

The notebook does not answer this question with a statistical model. It prepares for that work by checking the files, explaining their relationships, defining a possible study population, and measuring whether each transport category has enough observations.

# The data in plain English

The 2022 NextGen NHTS contains several related tables. A table's **grain** means what one row represents.

| Table | What one row represents | Expected key | Main use |
|---|---|---|---|
| Household | One surveyed household | `HOUSEID` | Income, household size, vehicle ownership, residential setting |
| Person | One person inside a household | `HOUSEID + PERSONID` | Age, sex, education, employment, driving status |
| Vehicle | One vehicle belonging to a household | `HOUSEID + VEHID` | Vehicle type, age, fuel, ownership and use |
| Trip | One trip made by one person | `TDCASEID` | Mode, purpose, time, distance, origin and destination conditions |

The trip table is the **fact table** because the future analysis normally uses one row per trip. The other tables provide information about the household, person, or vehicle connected to each trip.

## How the tables connect

- One household can contain many people.
- One household can own many vehicles.
- One household can generate many trips.
- One person can make many trips.
- One vehicle can be used for many trips.

`HOUSEID` identifies a household. `PERSONID` only identifies a person inside that household. Two households can both contain `PERSONID = 1`, so a person must always be identified with both `HOUSEID` and `PERSONID`.

For example:

| HOUSEID | PERSONID | Meaning |
|---:|---:|---|
| 100 | 1 | Person 1 in household 100 |
| 200 | 1 | A different person: person 1 in household 200 |

This is why joining or counting people with `PERSONID` alone is incorrect.

# How to open and run the notebook

The installed Anaconda `base` environment contains all required packages. Its Python executable is:

```text
C:\ProgramData\anaconda3\python.exe
```

Open Anaconda Navigator, launch JupyterLab or Jupyter Notebook from the base environment, and open:

```text
D:\StatProject\NHTS_2022_data_exploration.ipynb
```

Select:

```text
Kernel -> Change Kernel -> Python 3 (ipykernel)
```

Then choose **Restart Kernel and Run All Cells**. The notebook currently stores the kernel name `base`, but the registered Jupyter kernel is named `python3`. Selecting `Python 3 (ipykernel)` runs the notebook with the same Anaconda base Python.

# What each notebook section does

## 1. Environment diagnostic

The notebook prints the Python version, Python executable, working directory, and package versions. This confirms which environment is actually running the code.

Why it matters: Anaconda can contain several environments. A notebook may fail if Jupyter uses a different Python installation from the one containing the required packages.

## 2. Dataset structure

This section explains the four main tables, their keys, and their relationships. It introduces the idea that the final analytical dataset should normally contain one row per trip.

Why it matters: Joining tables without understanding their grain can duplicate trips and produce incorrect results.

## 3. Configuration and imports

The main setting is:

```python
DATA_DIR = Path("./Data")
```

This tells the notebook where to find the extracted CSV files. The path should identify the folder containing the files, not a ZIP file.

The notebook imports `pandas`, `numpy`, `matplotlib`, and `seaborn`. These packages load tables, calculate summaries, and create charts.

## 4. File discovery and loading

The notebook searches recursively for the household, person, trip, and vehicle CSV files. It also looks for an Excel codebook.

The files currently found are:

| Table | File | Rows | Columns |
|---|---|---:|---:|
| Household | `hhv2pub.csv` | 7,893 | 43 |
| Person | `perv2pub.csv` | 16,997 | 153 |
| Trip | `tripv2pub.csv` | 31,074 | 102 |
| Vehicle | `vehv2pub.csv` | 14,684 | 55 |

No Excel codebook is currently present. Download it from the official [NHTS documentation page](https://nhts.ornl.gov/documentation) and place it in `D:\StatProject\Data`.

## 5. Key validation

A **primary key** is a field, or combination of fields, that uniquely identifies a row. The notebook checks for null keys, duplicate keys, and the number of unique keys.

The current data pass these checks:

- Household: `HOUSEID` is unique.
- Person: `HOUSEID + PERSONID` is unique.
- Vehicle: `HOUSEID + VEHID` is unique.
- Trip: `TDCASEID` is unique.
- The trip composite key `HOUSEID + PERSONID + SEQ_TRIPID` is also unique.

Why it matters: A parent table with duplicate keys can cause one trip to appear several times after a join.

## 6. Relationship validation

The notebook checks whether every child record has a matching parent record.

Current results:

- Every person matches a household.
- Every vehicle matches a household.
- Every trip matches a household.
- Every trip matches a person.

All four relationships have a 100% match rate in the current files.

## 7. Codebook search

The `search_codebook(term)` function searches every cell in every Excel codebook sheet. It can search for a variable name such as `TRPTRANS` or an ordinary phrase such as `population density`.

The codebook is essential because an abbreviated variable name is not a complete definition. It explains what was asked, who received the question, what each numeric code means, and why some records have special values.

## 8. Column profiling

`column_profile(df)` summarizes every column. It reports data type, number of distinct values, ordinary missing values, special NHTS codes, and example values.

`inspect_variable(df, column, weight=None)` creates a frequency table for one variable. It can show both raw sample counts and survey-weighted totals.

Important special codes include:

| Code | General meaning |
|---:|---|
| `-1` | Appropriate or valid skip |
| `-7` | Prefer not to answer |
| `-8` | Do not know |
| `-9` | Not ascertained |

These values must not automatically be treated as the same kind of missing information. The individual variable's codebook entry determines the correct treatment.

## 9. Candidate-variable catalogue

The catalogue groups possible fields into identifiers, outcome, trip definition, distance, traveller, household, accessibility, and survey-design categories. It also shows which tables contain each field.

This step is an inventory, not a final variable selection. A variable appearing in the data does not mean it is appropriate for modelling.

## 10. Transport-mode mapping

The notebook converts detailed `TRPTRANS` codes into broader groups:

| Group | Included raw codes |
|---|---|
| Car | 01, 02, 03, 04 |
| Public transport | 08, 10, 11, 12, 13 |
| Cycling | 18 |
| Walking | 20 |
| Other or excluded | Every other code |

Keeping `other_or_excluded` during exploration makes the transformation transparent. Other modes are not silently deleted.

In the complete trip file, car accounts for 88.00% of raw records and approximately 86.69% of the seven-day weighted total.

## 11. Safe table joining

The trip table already contains many person and household fields. The notebook starts with the trip table and adds only fields that are missing from it. This avoids duplicate names such as `income_x` and `income_y`.

The person join uses `HOUSEID + PERSONID`. The household join uses `HOUSEID`. The number of trip rows remained 31,074 after both joins.

The join function should still be improved: it currently removes duplicate parent keys before validation and does not report unmatched records. Duplicate parent keys should instead cause a clear diagnostic error.

## 12. Proposed weekday commute population

The exploratory population applies four filters:

1. Person is at least 18 years old.
2. `TDWKND = 02`, meaning weekday.
3. `TRIPPURP = 01`, meaning home-based work.
4. Mode is car, public transport, walking, or cycling.

The resulting population contains:

| Measure | Correct result |
|---|---:|
| Trip records | 4,269 |
| Unique people | 2,384 |
| Unique households | 1,928 |

The notebook currently prints 6 unique people because it counts `PERSONID` alone. The correct calculation is:

```python
study_pop[["HOUSEID", "PERSONID"]].drop_duplicates().shape[0]
```

The sample contains 223 trips with a `TDAYDATE` in January 2023. These records belong to the survey cycle and are retained.

## 13. Survey weights

Survey weights allow records from the sample to represent a larger U.S. travelling population.

- `WTTRDFIN` is the seven-day trip weight.
- `WTTRDFIN5D` is the weekday trip weight.
- Raw counts show how many observations are available for statistical estimation.
- Weighted percentages estimate population travel shares.

A large weighted total cannot make a small raw sample statistically stable. Both results must always be displayed.

## 14. Feasibility assessment

The proposed four-category outcome has these results:

| Mode | Raw count | Raw share | Weekday weighted share | Interpretation |
|---|---:|---:|---:|---|
| Car | 4,062 | 95.15% | 94.86% | Large enough for initial analysis |
| Public transport | 77 | 1.80% | 2.09% | Small class; keep the model simple |
| Cycling | 31 | 0.73% | 0.67% | Small class; separate estimates may be unstable |
| Walking | 99 | 2.32% | 2.39% | Small class; keep the model simple |

A three-category alternative combines walking and cycling:

| Mode | Raw count | Weighted share |
|---|---:|---:|
| Car | 4,062 | 94.86% |
| Public transport | 77 | 2.09% |
| Active travel | 130 | 3.05% |

The three-category outcome is a reasonable primary option because it gives active travel a larger sample. The four-category outcome can remain a descriptive or sensitivity analysis. Public transport is still small, so the future model should use a limited number of parameters.

## 15. Leakage and interpretation warnings

**Outcome leakage** occurs when a predictor contains information that is only known after the traveller has chosen a mode.

- `TRVLCMIN` is the duration of the trip that actually occurred. It should not be treated as an ordinary pre-choice predictor.
- Transit waiting time is only observed for transit trips.
- `TRPMILES` may depend on the chosen route and mode.
- `GCDWORK` is a more mode-independent approximation of commute distance when available.

Vehicle ownership, residential density, and rail access also require careful interpretation. People may choose homes and vehicles partly according to existing travel preferences. These relationships are therefore associational, not automatically causal.

## 16. Predictor-quality inspection

This section examines distinct values, missingness, special codes, and whether fields are constant.

Its current automatic labels need improvement. NHTS variables such as `RAIL`, `URBRUR`, and `R_SEX_IMP` use numbers as category codes, but the notebook labels them numerical. A variable with two categories is also not necessarily nearly constant; near constancy depends on whether one value dominates almost all records.

Use these outputs as prompts for codebook review rather than final modelling decisions.

## 17. Optional export

Export is disabled by default:

```python
EXPORT_OUTPUT = False
```

Changing it to `True` writes the filtered study population to:

```text
D:\StatProject\nhts_weekday_commute_analysis.csv
```

Leave export disabled until the filters, missing-value rules, and selected variables have been reviewed.

## 18. Final interpretation checklist

The notebook ends with seven questions for every retained variable. They cover official definition, grain, timing, missing codes, relevance, confounding, and role in the analysis.

Modelling should begin only after this checklist has been completed for every outcome, predictor, identifier, and survey-design field.

# How to explore the data yourself

Follow this sequence whenever you investigate a variable.

## Step 1. Find the variable's official meaning

```python
search_codebook("HHVEHCNT")
```

Read the definition, question population, response codes, and special-code meanings.

## Step 2. Find which table contains it

Use the candidate-variable catalogue or check:

```python
"HHVEHCNT" in hh.columns
"HHVEHCNT" in per.columns
"HHVEHCNT" in trip.columns
```

## Step 3. Inspect its distribution

```python
inspect_variable(trip, "HHVEHCNT", weight="WTTRDFIN5D")
```

Look for dominant categories, rare values, negative special codes, and unexpected values.

## Step 4. Profile its data quality

```python
column_profile(trip).query("column == 'HHVEHCNT'")
```

Check ordinary missingness and special-code percentages separately.

## Step 5. Confirm its grain and timing

Ask what one value describes: household, person, trip, origin, or destination. Then ask whether the information existed before the mode choice. A field known only after the trip may introduce leakage.

## Step 6. Decide its role

Classify the field as an identifier, outcome, predictor, survey-design field, or field that should be excluded.

## Step 7. Record the decision

Create a working variable table with these columns:

| Variable | Official definition | Grain | Codes | Proposed role | Keep? | Reason |
|---|---|---|---|---|---|---|

This table becomes the bridge between data exploration and the research proposal.

# What to do next

Complete the following tasks in order.

1. Download the official Excel codebook and place it in `D:\StatProject\Data`.
2. Change the notebook's Jupyter kernel metadata to the installed `python3` kernel or select `Python 3 (ipykernel)` manually.
3. Correct the unique-person calculation to use `HOUSEID + PERSONID`.
4. Improve join validation so duplicate parent keys are diagnosed rather than silently removed and unmatched records are reported.
5. Add `R_AGE_IMP` to the catalogue as unavailable; document `R_AGE` as the available age field.
6. Review the codebook definitions and frequencies for every filter: `R_AGE`, `TDWKND`, `TRIPPURP`, and `TRPTRANS`.
7. Complete the interpretation checklist for every candidate variable.
8. Select a small set of predictors. Avoid including several measures that represent nearly the same concept.
9. Use the three-category outcome as the likely primary analysis and retain the four-category outcome for descriptive comparison.
10. Write the proposal's data and methods sections using the confirmed population, outcome definition, weight, and limitations.
11. Only after these decisions are documented should modelling begin.

# Suggested proposal structure

Use the following order for the research proposal:

1. Research title
2. Background and planning problem
3. Research gap
4. Research question
5. Research objectives
6. Conceptual framework
7. NHTS data source
8. Study population and unit of analysis
9. Outcome definition
10. Predictor-selection rationale
11. Missing-data and survey-weight treatment
12. Proposed statistical analysis
13. Limitations and non-causal interpretation
14. Ethical considerations
15. Expected contribution
16. Timeline
17. References

A defensible primary research question is:

> Among adults making weekday home-based work trips in the United States, how are traveller, household, commute-distance, and accessibility characteristics associated with choosing car, public transport, or active travel?

The proposal can describe a future multinomial mode-choice model, but it should not claim that the notebook has already estimated one. The current work establishes the data foundation needed to choose and justify that model.

# Official resources

- NHTS data: https://nhts.ornl.gov/downloads
- NHTS documentation: https://nhts.ornl.gov/documentation


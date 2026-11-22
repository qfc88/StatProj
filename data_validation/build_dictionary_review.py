"""Build only the opening and first dictionary review of the duration notebook."""

from pathlib import Path
import hashlib
import json

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "NHTS_2022_commute_duration.ipynb"
SNAPSHOT = ROOT / "data_validation/dictionary_review_source_snapshot.json"

# Record source integrity before creating or executing the new notebook.
protected = sorted((ROOT / "Data").iterdir()) + sorted(ROOT.glob("*.ipynb"))
snapshot = {
    str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in protected if p.is_file() and p != OUTPUT
}
if not SNAPSHOT.exists():
    SNAPSHOT.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")


def markdown(text):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text):
    return nbf.v4.new_code_cell(text.strip())


cells = [
    markdown("""
# Predicting weekday commute duration with the 2022 NHTS

**StatProj | LS03 - Team 1**  
**Current milestone:** Source inspection and Data Dictionary, Part 1.  
**Review date:** 15 November 2026 (Asia/Singapore).

For adults making weekday home-based work trips in the United States, how accurately
can home-work distance, planned transport mode, departure period, trip direction,
and broad residential context predict reported trip duration immediately before departure,
once the planned mode is known?

The unit of observation is one trip record. The target is `TRVLCMIN`, in minutes.
The intended estimand is the **conditional median of duration given the predictors**.
This is a research choice from the project context, not an EDA finding. Claims will be
predictive and associational. Any change to this estimand requires review before modeling.

This installment contains no analytical sample construction, distributional EDA,
correlation, imputation, model fitting, or test-set evaluation.
"""),
    markdown("""
## 1. Evidence status and existing work

| Evidence category | Current status |
|---|---|
| Proposal and study design | The proposed population is adults aged at least 18, weekday home-based work trips, and car/public transport/walking/cycling. The conditional median and household-grouped validation remain the intended design. Instructor approval has not been established in this session. |
| Historical project artifacts | `NHTS_2022_data_exploration.ipynb`, `NHTS_2022_correlation_analysis.ipynb`, and `NHTS_2022_research_directions.ipynb` contain saved outputs. Some address mode choice or analyze the full sample. They were inspected as historical work and were not rerun. |
| Historical validation | `data_validation/validation_report.md` reports PASS with generation date 17 October 2026. Its reported key checks, row counts, and control totals were not reproduced here. |
| Proposal quantities | Approximately 4,269 trips, 2,384 people, 1,928 households, the reported mode counts, missingness, and extreme durations are proposal/historical quantities. They are not new verified results from this installment. |
| Documentation verification | The live official Codebook PDF was reopened and identifies Version 2.1, April 2025. The first dictionary entries below were cross-checked against the local Codebook and Data Dictionary sheets and the corresponding PDF entries. |
| Checks executed in this installment | Interpreter/package diagnostics; raw CSV headers and a two-record structural preview per file; header coverage against the local official reference workbooks; extraction of codebook definitions/codes for the first ten entries. No population estimates were calculated. |

Previous full-sample exploration means future holdout results cannot be described as
having had no prior exploratory exposure. Before splitting or modeling, review that
history and document the validation limitation. This installment does not create or
open a final test partition and does not use historical associations to choose features.
"""),
    markdown("""
## 2. Environment and source files

The terminal's default `python` resolves to `C:/Python313/python.exe` (3.13.5),
which lacks the analysis packages. The existing Conda `base` interpreter at
`C:/ProgramData/anaconda3/python.exe` (3.12.7) has the packages needed here.
The registered `python3` kernelspec points to that Conda interpreter. The three
existing notebooks declare either `base` or `python3`; metadata alone does not
identify the live kernel selected in the user's IDE.

Existing Conda environment paths `base`, `py11`, and `pillbox` were found in the
local environment registry and their Python executables exist. Other environments
were not inspected. No environment was created and no packages were installed or upgraded.
Run the following diagnostic in the selected notebook kernel to verify its interpreter.
"""),
    code("""
import sys
from pathlib import Path
from importlib import metadata

print("Python executable:", sys.executable)
print("Python version:", sys.version.split()[0])
PROJECT_ROOT = Path.cwd().resolve()
if not (PROJECT_ROOT / "Data").is_dir():
    raise FileNotFoundError("Open this notebook from the StatProject project root.")
DATA_DIR = PROJECT_ROOT / "Data"
print("Project root:", PROJECT_ROOT)
for package in ["pandas", "numpy", "seaborn", "matplotlib", "scikit-learn",
                "statsmodels", "nbformat", "openpyxl", "ipykernel"]:
    try:
        version = metadata.version(package)
    except metadata.PackageNotFoundError:
        version = "Not installed"
    print(f"{package}: {version}")
"""),
    markdown("""
### 2.1 File identification and header inventory

The existing `Data/` folder contains five CSV files, two V2.1 reference workbooks,
and `Citation.pdf`. CSV names containing `v2pub` alone do not prove the minor release.
The local V2.1 workbook labels, matching headers, the live V2.1 PDF, and the historical
validation provide release-consistency evidence. A fresh byte-for-byte comparison
against the official CSV download has not been performed.

This cell reads each CSV header and only its first two records as text to check basic
structure and preserve leading zeros. It prints identifier columns only; it does not
inspect outcome/predictor distributions or estimate analytical sample sizes. The Long
Distance file is inventoried for completeness and is outside the current trip-duration scope.
"""),
    code("""
import csv

csv_headers = {}
for source_path in sorted(DATA_DIR.iterdir()):
    if source_path.is_file():
        print(f"{source_path.name}: {source_path.stat().st_size:,} bytes")

for source_path in sorted(DATA_DIR.glob("*.csv")):
    with source_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        csv_headers[source_path.name] = list(reader.fieldnames or [])
        preview = [next(reader, None) for _ in range(2)]
    print(f"\\n{source_path.name}: {len(csv_headers[source_path.name])} columns")
    print("Header:", ", ".join(csv_headers[source_path.name]))
    identifier_columns = [name for name in ["HOUSEID", "PERSONID", "VEHID", "TDCASEID"]
                          if name in csv_headers[source_path.name]]
    print("Structural preview (identifiers only):",
          [{name: row[name] for name in identifier_columns}
           for row in preview if row is not None])

assert "GCDWORK" in csv_headers["perv2pub.csv"]
assert "GCDWORK" not in csv_headers["tripv2pub.csv"]
print("\\nGCDWORK is available in Person and requires a validated join to Trip later.")
"""),
    markdown("""
## 3. Data Dictionary: Part 1

The table describes **what the variables mean**. It does not finalize preprocessing
or the predictor set. Project roles are determined by the research question; candidate
predictors require later review. All ten entries are existing public-use variables,
including variables derived by the data provider. No study-derived variable is created.

**Reference convention:** [CB] is FHWA, *2022 NextGen NHTS Public Use Codebook*,
Version 2.1 (April 2025), [official PDF](https://nhts.ornl.gov/media/2022/doc/codebook.pdf).
Page numbers below are one-based PDF pages. Local sheet/row locators refer to
`Data/NHTS_2022_Codebook_V2.1.xlsx`. [DD] is FHWA, *2022 NextGen NHTS Data Dictionary*,
local V2.1 copy `Data/NHTS_2022_Data_Dictionary_V2.1.xlsx`, sheet `Dictionary`, available
via the [official documentation page](https://nhts.ornl.gov/documentation).
The combined root-level `NHTS_2022_complete_data_dictionary.xlsx` is a working reference
and is not used as the evidence source.

**Type convention:** `C` and `N` are the provider's character and numeric types.
Pandas' inferred dtype does not determine whether a variable is categorical. Numeric
response ranges below describe the published release and are not automatic exclusion
thresholds. "None listed" refers only to the variable's codebook entry; it is not a
claim that the local CSV has no blank or invalid values. Each variable's special codes
must be handled separately. No universal negative-value recode is applied.

### 3.1 Outcome and population filters

| Exact variable name | Source table/file | Official definition | Interpretation for this study | Data type and unit | Valid codes/ranges in release | Missing and skip codes | Source document, version, page/sheet and URL | Project role | Initial status | Original or study-derived |
|---|---|---|---|---|---|---|---|---|---|---|
| `TRVLCMIN` | Trip, `tripv2pub.csv` | Trip Duration in Minutes | Reported duration of one trip record; target for the intended conditional median. | N; minutes | Published response range 0-1425. Zero is included in the source range; no positive-duration filter is adopted here. | `-9` = Not ascertained; no other special code listed. | [CB](https://nhts.ornl.gov/media/2022/doc/codebook.pdf), V2.1, p. 58; Trip rows 545-546. [DD](https://nhts.ornl.gov/documentation), V2.1, Dictionary row 207. | Target | Required supporting variable | Original public-use field, not study-derived |
| `R_AGE` | Trip, `tripv2pub.csv`; also Person and Long Distance | Respondent age | Proposed adult eligibility: age at least 18. Additional use as a predictor remains undecided. | N; years | Published response range 5-92. | None listed for this entry. | [CB](https://nhts.ornl.gov/media/2022/doc/codebook.pdf), V2.1, p. 54; Trip row 393. [DD](https://nhts.ornl.gov/documentation), V2.1, Dictionary row 171. | Filter | Required supporting variable | Original public-use field, not study-derived |
| `TDWKND` | Trip, `tripv2pub.csv` | Weekend trip | Proposed weekday eligibility: code `02`. This is a categorical indicator. | C, length 2; no physical unit | `01` = Weekend; `02` = Weekday. | None listed for this entry. | [CB](https://nhts.ornl.gov/media/2022/doc/codebook.pdf), V2.1, p. 56; Trip rows 462-463. [DD](https://nhts.ornl.gov/documentation), V2.1, Dictionary row 198. | Filter | Required supporting variable | Original public-use field, not study-derived |
| `TRIPPURP` | Trip, `tripv2pub.csv` | General purpose of trip | Proposed HBW eligibility: code `01`. Detailed construction and implications for chained journeys remain pending. | C, length 2; no physical unit | `01` = Home-based work; `02` = Home-based shopping; `03` = Home-based social/recreational; `04` = Home-based other; `05` = Not a home-based trip. | `-9` = Not ascertained; no other special code listed. | [CB](https://nhts.ornl.gov/media/2022/doc/codebook.pdf), V2.1, p. 57; Trip rows 514-519. [DD](https://nhts.ornl.gov/documentation), V2.1, Dictionary row 202. | Filter | Required supporting variable | Original public-use field, not study-derived |

### 3.2 Identifiers and proposed survey weight

| Exact variable name | Source table/file | Official definition | Interpretation for this study | Data type and unit | Valid codes/ranges in release | Missing and skip codes | Source document, version, page/sheet and URL | Project role | Initial status | Original or study-derived |
|---|---|---|---|---|---|---|---|---|---|---|
| `HOUSEID` | All five CSVs; analysis base: `tripv2pub.csv` | Unique Identifier- Household | Household grouping for future partitioning and joins. All trips in a household must remain in one partition. Uniqueness in the household table is to be rechecked later. | C, length 10; identifier | Published identifier span 9000013002-9000218040; preserve as text. | None listed for this entry. | [CB](https://nhts.ornl.gov/media/2022/doc/codebook.pdf), V2.1, p. 49; Trip row 215. [DD](https://nhts.ornl.gov/documentation), V2.1, Dictionary row 83. | ID | Required supporting variable | Original public-use field, not study-derived |
| `PERSONID` | Person, Trip, Long Distance; `perv2pub.csv`, `tripv2pub.csv`, `ldtv2pub.csv` | Person ID within household | Person linkage uses `HOUSEID` plus `PERSONID`; `PERSONID` alone is not a globally unique person identifier. | C, length 2; identifier | Published Trip codes `01`-`09`; preserve leading zeros. | None listed for this entry. | [CB](https://nhts.ornl.gov/media/2022/doc/codebook.pdf), V2.1, pp. 53-54; Trip rows 368-376. [DD](https://nhts.ornl.gov/documentation), V2.1, Dictionary row 155. | ID | Required supporting variable | Original public-use field, not study-derived |
| `TDCASEID` | Trip, `tripv2pub.csv` | Unique identifier for every trip record in the file | Trip-level provenance and duplicate checks. Actual key uniqueness is to be rechecked at the key-validation milestone. | C, length 14; identifier | Published identifier span 90000130020101-90002180400103; preserve as text. | None listed for this entry. | [CB](https://nhts.ornl.gov/media/2022/doc/codebook.pdf), V2.1, p. 56; Trip row 461. [DD](https://nhts.ornl.gov/documentation), V2.1, Dictionary row 197. | ID | Required supporting variable | Original public-use field, not study-derived |
| `WTTRDFIN5D` | Trip, `tripv2pub.csv` | 5 day National trip weight | Proposed weekday summary and evaluation weight. Its normalization, eligible records, and interpretation of totals still require the weighting documentation. Training weights are a separate design decision. | N; survey expansion weight | Published response range 0-285950601.31. Zero is included in the source range and is not automatically missing. | No special missing/skip code listed. | [CB](https://nhts.ornl.gov/media/2022/doc/codebook.pdf), V2.1, p. 62; Trip row 680. [DD](https://nhts.ornl.gov/documentation), V2.1, Dictionary row 269. | Weight | Required supporting variable; usage pending verification | Original public-use field, not study-derived |

### 3.3 Home-work distance and leakage boundary

| Exact variable name | Source table/file | Official definition | Interpretation for this study | Data type and unit | Valid codes/ranges in release | Missing and skip codes | Source document, version, page/sheet and URL | Project role | Initial status | Original or study-derived |
|---|---|---|---|---|---|---|---|---|---|---|
| `GCDWORK` | Person only, `perv2pub.csv`; absent from raw Trip | Great circle distance (miles) between home and work | Candidate home-work separation measure, not route distance. Join to trips later using validated person keys. Applicability, derivation, and availability at prediction time require further documentation. | N; miles | Published response range 0-2543.9541665. Zero is a documented response value, not a missing code. | `-1` = Appropriate skip; `-9` = Not ascertained. Exact skip conditions pending verification; do not combine them automatically. | [CB](https://nhts.ornl.gov/media/2022/doc/codebook.pdf), V2.1, p. 14; Person rows 184-186. [DD](https://nhts.ornl.gov/documentation), V2.1, Dictionary row 63. | Predictor | Candidate; applicability pending verification | Original public-use field, not study-derived |
| `TRPMILES` | Trip, `tripv2pub.csv` | Calculated Trip distance converted into miles | Realized trip distance. Excluded from all pre-departure prediction pipelines by the study's leakage rule; a separate leakage diagnostic may be considered later. | N; miles | Published response range 0-4859.4769818. | `-9` = Not ascertained; no other special code listed. | [CB](https://nhts.ornl.gov/media/2022/doc/codebook.pdf), V2.1, p. 57; Trip rows 523-524. [DD](https://nhts.ornl.gov/documentation), V2.1, Dictionary row 205. | Diagnostic | Excluded from predictors | Original public-use field, not study-derived |

All remaining columns are inventoried by exact name in the structural output above.
Their study definitions, applicability, and missing/skip logic remain **Pending
verification**. The next dictionary group is `TRPTRANS`, `STRTTIME`, `WHYFROM`, `WHYTO`,
and residential-context variables. In particular, `TRPTRANS` records realized mode;
using it to represent a planned mode requires an explicit assumption and limitation.
"""),
    markdown("""
### 3.4 Reproducible reference checks

The following cell compares all CSV headers with the table-membership markers in the
local official Data Dictionary and the names in each Codebook sheet. It then prints
only definitions/codes for the ten entries above, without published frequency or
weighted totals. This is a schema/reference check, not validation of all observed values.
"""),
    code("""
from openpyxl import load_workbook

table_sources = {
    "hhv2pub.csv": ("Household", "HH"),
    "perv2pub.csv": ("Person", "PER"),
    "vehv2pub.csv": ("Vehicle", "VEH"),
    "tripv2pub.csv": ("Trip", "TRIP"),
    "ldtv2pub.csv": ("Long Distance", "LDT"),
}
review_variables = ["TRVLCMIN", "R_AGE", "TDWKND", "TRIPPURP", "HOUSEID",
                    "PERSONID", "TDCASEID", "WTTRDFIN5D", "GCDWORK", "TRPMILES"]
codebook_path = DATA_DIR / "NHTS_2022_Codebook_V2.1.xlsx"
dictionary_path = DATA_DIR / "NHTS_2022_Data_Dictionary_V2.1.xlsx"
codebook = load_workbook(codebook_path, read_only=True, data_only=True)
dictionary = load_workbook(dictionary_path, read_only=True, data_only=True)
try:
    dictionary_rows = list(dictionary["Dictionary"].values)
    dictionary_header = list(dictionary_rows[0])
    matched_occurrences = 0
    for filename, (sheet_name, marker) in table_sources.items():
        marker_index = dictionary_header.index(marker)
        documented = {row[0] for row in dictionary_rows[1:]
                      if row[marker_index] is not None and str(row[marker_index]).strip()}
        codebook_names = {row[0] for row in codebook[sheet_name].values
                          if row[0] and row[0] != "Name"}
        actual = set(csv_headers[filename])
        assert actual == documented, f"Data Dictionary header mismatch: {filename}"
        assert actual == codebook_names, f"Codebook header mismatch: {filename}"
        matched_occurrences += len(actual)
        print(f"{filename}: {len(actual)} column names match both reference sheets.")
    print("Total table-column occurrences matched:", matched_occurrences)

    for variable in review_variables:
        sheet_name = "Person" if variable == "GCDWORK" else "Trip"
        current_variable = None
        print(f"\\n{variable} | {sheet_name}")
        for row_number, row in enumerate(codebook[sheet_name].values, start=1):
            if row[0]:
                current_variable = row[0]
            if current_variable == variable:
                print(f"  row {row_number}: {row[:5]}")
finally:
    codebook.close()
    dictionary.close()
"""),
    markdown("""
## 4. Domain Caveats

These are questions for later documentation review and training-data EDA, not findings
about the current analytical population.

| Topic | Documentation established so far | Investigation still required |
|---|---|---|
| Trip chaining | [CB], V2.1, p. 57 labels `TRIPPURP=01` as home-based work. The unit here is a trip record. | Read the official Derived Variables documentation to establish how `TRIPPURP` is constructed and how intermediate stops relate to HBW. Do not assume one record represents an entire commute journey. |
| Duration heaping | [CB], V2.1, p. 58 describes duration in minutes; no training distribution was examined here. | On training data, check concentration at 5, 10, 15, and 30 minutes and describe possible rounding. Do not automatically smooth, alter, or delete these values. |
| Distance missingness | [CB], V2.1, p. 14 distinguishes `GCDWORK=-1` (Appropriate skip) and `-9` (Not ascertained). | Verify derivation and skip conditions, then examine training-data missingness by relevant groups. Choose handling after review. EDA alone cannot establish MCAR, MAR, or MNAR. |
| Planned versus realized information | The prediction question assumes mode is known before departure. | Verify mode, departure-time, and direction fields in the next dictionary group. State the assumption when realized survey fields proxy information available before departure. |

The official [documentation page](https://nhts.ornl.gov/documentation) is the entry point
for the Derived Variables and weighting references; those details remain pending in this installment.
"""),
    markdown("""
## 5. Review checkpoint

The structural checks found 43 Household, 153 Person, 55 Vehicle, 102 Trip, and 74
Long Distance columns. All 427 table-column occurrences match the names in both
local reference workbooks. This is a result of the executed header checks, not a count
of unique variables, trips, people, or households. The two-record previews read
successfully. `GCDWORK` is present only in Person, and household residential density
fields `HBPPOPDN` and `HTPPOPDN` are also absent from the raw Trip header. Any later
joins must validate keys and preserve trip row counts.

Review this first dictionary group before extending it. The unresolved items are the
HBW derivation, `GCDWORK` applicability/skip logic, weighting usage, and the remaining
predictor definitions. No imputation, transformation, grouping, outlier exclusion,
training-weight choice, fallback threshold, or model list has been finalized here.
The future **Variable Decisions and Preprocessing** section will be written after
training-data EDA and review, separately from the Data Dictionary.
"""),
]

notebook = nbf.v4.new_notebook(cells=cells)
notebook.metadata = {
    "kernelspec": {"display_name": "Python 3 (ipykernel)", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.12.7"},
}
nbf.validate(notebook)
nbf.write(notebook, OUTPUT)
print(f"Created {OUTPUT.name}: {len(cells)} cells, three code cells, dictionary review only.")

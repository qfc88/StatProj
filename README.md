# Predicting weekday commute duration with the 2022 NHTS

StatProj, LS03 – Team 1.

**Question.** For adults making weekday home-based work trips in the United States, how
accurately can home–work distance, transport mode, departure time, trip direction and
residential context predict reported trip duration before departure? The target is the
conditional median of `TRVLCMIN` (minutes). Claims are predictive and associational.

**Status.** The exploratory data analysis (EDA) is complete. The team is now building and
comparing prediction methods against a median baseline.

**New to the project? Start with [`docs/START_HERE.md`](docs/START_HERE.md).**

## Quick start

```text
Windows:        double-click setup.cmd   (or: powershell -ExecutionPolicy Bypass -File setup.ps1)
macOS / Linux:  bash setup.sh
```

The setup creates `.venv/`, installs `requirements.txt` (Python 3.10–3.13), builds the fake
test data and runs the checks. Then tell your AI assistant your name; it reads `AGENTS.md`.

## Repository layout

| Path | Content |
|---|---|
| `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md` | Rules and tutoring guide for AI assistants |
| `docs/` | Start guide, background and glossary, Git workflow, integration hand-offs, changes from the proposal, one guide per member |
| `CONTRACT.md` | File formats shared by the three parts and the expected counts |
| `src/` | Modelling code; each file has one owner (`docs/team/README.md`) |
| `tests/` | Checks of the shared contract |
| `NHTS_2022_commute_duration.ipynb` | Completed EDA notebook (read-only) |
| `Data/` | Raw NHTS 2022 V2.1 public-use files |
| `outputs/` | Generated tables, not committed |
| `Q4_project_proposal.md`, `PROJECT_REQUIREMENTS.txt`, `PROJECT_BASELINE.txt`, `Project_Rules_and_Rubric(3).pdf` | Proposal and course rules |
| `AI_USE.md` | AI-use log required by the course |
| `data_validation/`, other notebooks and scripts | Earlier project history; not needed to run the code |

## Data

`Data/` contains (names are case-sensitive on Linux and Colab): `hhv2pub.csv`,
`perv2pub.csv`, `tripv2pub.csv`, `vehv2pub.csv`, `ldtv2pub.csv`,
`NHTS_2022_Codebook_V2.1.xlsx`, `NHTS_2022_Data_Dictionary_V2.1.xlsx`, `Citation.pdf`.

Source: Federal Highway Administration (2022), *2022 NextGen National Household Travel
Survey Core Data*, U.S. Department of Transportation, Washington, DC,
<https://nhts.ornl.gov>. Documentation: <https://nhts.ornl.gov/documentation>.

## Run order

Run every command from the repository root with the environment activated.

| Step | Owner | Command | Output |
|---|---|---|---|
| – | anyone | `python -m src.status --name <you>` | what exists, what is pending, your next step |
| 0 | anyone | `python -m src.make_fixture` | fake tables in `outputs/fixture/` for testing |
| 1 | Jovie | `python -m src.prepare_data` | `outputs/modelling/train.csv`, `test.csv` |
| 2 | Anthony | `python -m src.validation` | `outputs/validation/folds.csv` |
| 3 | Galvin | `python -m src.models` | `outputs/predictions/predictions.csv` |
| 4 | Anthony | `python -m src.evaluate` | `outputs/evaluation/metrics.csv` |

Steps 2–4 accept `--fixture` to run on the fake data before the real tables exist.
Numbers from the fixture never go into the report.

## Team rules

- Each person works on their own branch (`feature/<name>-<task>`) and edits only the files
  they own. Changes to the contract go through a separate pull request.
- Pull requests are reviewed by a teammate: Jovie reviews Anthony, Anthony reviews Galvin,
  Galvin reviews Jovie.
- The Test table is scored once, after the chosen model is written down.
- Record AI use in `AI_USE.md` (tool, date, purpose, representative prompts, what was
  generated and how it was checked), each person in their own section.

## Environment

The EDA ran in Conda with Python 3.12.7, pandas 2.2.2, numpy 1.26.4, openpyxl 3.1.5,
matplotlib 3.9.2, scikit-learn 1.5.1 and statsmodels 0.14.2. The setup script was also
checked with Python 3.13.5, pandas 2.2.3 and numpy 2.2.6: the household split reproduced
the EDA fingerprint (`CONTRACT.md`, section 3).

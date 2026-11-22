"""Data preparation (owner: Galvin).

    python -m src.prepare_data

Goal: rebuild the EDA sample from Data/ and write outputs/modelling/train.csv and test.csv
in the format of CONTRACT.md, section 4.

Read in the notebook NHTS_2022_commute_duration.ipynb (search for these titles):
- "Study sample construction": age, calendar weekday and trip-purpose rules.
- "# Split the study sample by household": the exact split (sorted HOUSEID, seed 42).
- "Variable Decisions and Preprocessing": target and predictor decisions.

Expected counts are in CONTRACT.md, section 3. If a count differs, stop and report it.
Do not change a rule only to match a number.
"""

from src import contract
from src.paths import PERSON_CSV, TRIP_CSV, output_paths

EXPECTED = {"eda_trips": 4393, "train_trips": 3516, "test_trips": 877, "modelling_train_rows": 3484}


def build_modelling_tables():
    """Return (train, test) DataFrames with the columns in contract.TRIP_COLUMNS.

    Steps to implement:
    1. Read Trip and Person columns as text (dtype="string", keep_default_na=False).
    2. Apply the EDA filters and check the 4,393 trips.
    3. Split households exactly as in the notebook, before any mode or target filter.
    4. Join GCDWORK from Person on HOUSEID + PERSONID (many-to-one, row count kept).
    5. Recode columns as listed in CONTRACT.md, section 4.
    """
    raise NotImplementedError("Galvin: implement build_modelling_tables()")


def main() -> None:
    train, test = build_modelling_tables()
    contract.check_trip_table(train, "train")
    contract.check_trip_table(test, "test")
    contract.check_households_separate(train, test)
    fingerprint = contract.train_household_fingerprint(train["HOUSEID"])
    if fingerprint != contract.EXPECTED_TRAIN_HOUSEHOLD_SHA256:
        raise contract.ContractError("Train households differ from the EDA split. Stop and report.")
    paths = output_paths()
    paths["train"].parent.mkdir(parents=True, exist_ok=True)
    train.to_csv(paths["train"], index=False)
    test.to_csv(paths["test"], index=False)
    print("Train trips:", len(train), "| Test trips:", len(test),
          "| modelling Train rows:", len(contract.modelling_rows(train)))


if __name__ == "__main__":
    main()

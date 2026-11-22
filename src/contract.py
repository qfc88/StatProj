"""Shared file formats from CONTRACT.md, with checks.

Run a check before handing a file to a teammate. A check raises ``ContractError``
with every problem it found.
"""

import hashlib
from pathlib import Path

import pandas as pd

# SHA-256 of the sorted Train HOUSEIDs from the EDA split (CONTRACT.md, section 3).
EXPECTED_TRAIN_HOUSEHOLD_SHA256 = "21cddffc9cfa109e97973155efd0100038c68d0d2b41f95eb3760f221fccc23f"

TARGET = "duration_min"
WEIGHT = "trip_weight"
PREDICTORS = [
    "distance_miles", "distance_status", "mode_group",
    "departure_minute", "direction", "residential_context",
]
TRIP_COLUMNS = [
    "TDCASEID", "HOUSEID", "PERSONID", TARGET, "distance_miles", "distance_status",
    "trptrans_code", "mode_group", "in_main_scope", "departure_minute", "direction",
    "residential_context", WEIGHT,
]
TEXT_COLUMNS = [
    "TDCASEID", "HOUSEID", "PERSONID", "distance_status", "trptrans_code",
    "mode_group", "direction", "residential_context",
]
DISTANCE_STATUSES = {"recorded", "appropriate_skip", "not_ascertained"}
MODE_GROUPS = {"car_van_suv_pickup", "public_transit", "walk", "bike", "other"}
DIRECTIONS = {"home_to_work", "work_to_home"}
RESIDENTIAL_CONTEXTS = {"urban", "rural"}
N_FOLDS = 5
FOLD_COLUMNS = ["TDCASEID", "HOUSEID", "fold"]
PREDICTION_COLUMNS = ["TDCASEID", "fold", "model", "prediction_min"]


class ContractError(ValueError):
    """A file does not follow CONTRACT.md."""


def _raise_if(problems: list, name: str) -> None:
    if problems:
        raise ContractError(f"{name} breaks the contract:\n- " + "\n- ".join(problems))


def read_csv(path: Path) -> pd.DataFrame:
    """Read a contract file, keeping ID and code columns as text (leading zeros kept)."""
    text_dtypes = {c: "string" for c in TEXT_COLUMNS + ["model"]}
    return pd.read_csv(path, dtype=text_dtypes)


def check_trip_table(df: pd.DataFrame, name: str = "trip table") -> None:
    """Check train.csv / test.csv (all trips of one partition)."""
    problems = []
    missing = [c for c in TRIP_COLUMNS if c not in df.columns]
    extra = [c for c in df.columns if c not in TRIP_COLUMNS]
    if missing:
        problems.append(f"missing columns: {missing}")
    if extra:
        problems.append(f"unexpected columns: {extra}")
    if missing:
        _raise_if(problems, name)
    if df["TDCASEID"].isna().any() or df["TDCASEID"].duplicated().any():
        problems.append("TDCASEID must be present and unique")
    if df["HOUSEID"].isna().any():
        problems.append("HOUSEID must be present")
    for column, allowed in [("distance_status", DISTANCE_STATUSES), ("mode_group", MODE_GROUPS),
                            ("direction", DIRECTIONS), ("residential_context", RESIDENTIAL_CONTEXTS)]:
        bad = sorted(set(df[column].dropna()) - allowed)
        if bad or df[column].isna().any():
            problems.append(f"{column} has values outside {sorted(allowed)}: {bad or 'empty values'}")
    duration = df[TARGET]
    if (duration.dropna() < 0).any():
        problems.append("duration_min must be 0 or more (empty when not ascertained)")
    recorded = df["distance_status"] == "recorded"
    if df.loc[recorded, "distance_miles"].isna().any() or (df.loc[recorded, "distance_miles"] < 0).any():
        problems.append("distance_miles must be 0 or more when distance_status = recorded")
    if df.loc[~recorded, "distance_miles"].notna().any():
        problems.append("distance_miles must be empty unless distance_status = recorded")
    scope = df["in_main_scope"].astype("boolean")
    if scope.isna().any() or (scope != (df["mode_group"] != "other")).any():
        problems.append("in_main_scope must be True exactly when mode_group is not 'other'")
    minute = df["departure_minute"]
    if minute.isna().any() or (minute < 0).any() or (minute > 1439).any() or (minute % 1 != 0).any():
        problems.append("departure_minute must be an integer from 0 to 1439")
    if df[WEIGHT].isna().any() or (df[WEIGHT] <= 0).any():
        problems.append("trip_weight must be greater than 0")
    _raise_if(problems, name)


def modelling_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Rows used for modelling: main mode scope and an observed duration."""
    keep = df["in_main_scope"].astype(bool) & df[TARGET].notna()
    return df.loc[keep].reset_index(drop=True)


def load_modelling_table(path: Path) -> pd.DataFrame:
    """Read train.csv or test.csv, check it, and return the modelling rows."""
    df = read_csv(path)
    check_trip_table(df, name=str(path))
    return modelling_rows(df)


def train_household_fingerprint(house_ids) -> str:
    """SHA-256 of the sorted unique HOUSEIDs, one per line. Compare with
    EXPECTED_TRAIN_HOUSEHOLD_SHA256 to confirm the split matches the EDA household by household."""
    joined = "\n".join(sorted(set(map(str, house_ids))))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def check_households_separate(train: pd.DataFrame, test: pd.DataFrame) -> None:
    """No household may appear in both Train and Test."""
    shared = set(train["HOUSEID"]) & set(test["HOUSEID"])
    _raise_if([f"{len(shared)} households appear in both Train and Test"] if shared else [],
              "Train/Test split")


def check_folds(folds: pd.DataFrame, modelling_train: pd.DataFrame) -> None:
    """Check folds.csv against the modelling Train rows."""
    problems = []
    if list(folds.columns) != FOLD_COLUMNS:
        problems.append(f"columns must be {FOLD_COLUMNS}, found {list(folds.columns)}")
        _raise_if(problems, "folds")
    if folds["TDCASEID"].duplicated().any():
        problems.append("each TDCASEID must appear once")
    if set(folds["TDCASEID"]) != set(modelling_train["TDCASEID"]):
        problems.append("TDCASEID set must equal the modelling Train rows")
    if not folds["fold"].isin(range(1, N_FOLDS + 1)).all():
        problems.append(f"fold must be an integer from 1 to {N_FOLDS}")
    if (folds.groupby("HOUSEID")["fold"].nunique() > 1).any():
        problems.append("all trips of a household must be in the same fold")
    _raise_if(problems, "folds")


def check_predictions(predictions: pd.DataFrame, folds: pd.DataFrame) -> None:
    """Check predictions.csv against folds.csv."""
    problems = []
    if list(predictions.columns) != PREDICTION_COLUMNS:
        problems.append(f"columns must be {PREDICTION_COLUMNS}, found {list(predictions.columns)}")
        _raise_if(problems, "predictions")
    if predictions["prediction_min"].isna().any():
        problems.append("prediction_min must not be empty")
    if predictions.duplicated(["TDCASEID", "model"]).any():
        problems.append("one row per (TDCASEID, model)")
    expected = folds.set_index("TDCASEID")["fold"]
    for model, rows in predictions.groupby("model"):
        if set(rows["TDCASEID"]) != set(expected.index):
            problems.append(f"model {model!r} must predict every trip in folds.csv")
        elif (rows.set_index("TDCASEID")["fold"] != expected.loc[rows["TDCASEID"]].to_numpy()).any():
            problems.append(f"model {model!r} has fold numbers that differ from folds.csv")
    _raise_if(problems, "predictions")

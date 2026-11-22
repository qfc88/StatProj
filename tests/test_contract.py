"""The fake fixture must pass every contract check, and the checks must catch broken files."""

import pandas as pd
import pytest

from src import contract
from src.make_fixture import build_fixture


@pytest.fixture()
def fixture_paths(tmp_path):
    paths = {
        "train": tmp_path / "modelling" / "train.csv",
        "test": tmp_path / "modelling" / "test.csv",
        "folds": tmp_path / "validation" / "folds.csv",
        "predictions": tmp_path / "predictions" / "predictions.csv",
    }
    build_fixture(paths)
    return paths


def test_fixture_passes_all_checks(fixture_paths):
    train = contract.load_modelling_table(fixture_paths["train"])
    test = contract.load_modelling_table(fixture_paths["test"])
    contract.check_households_separate(train, test)
    folds = contract.read_csv(fixture_paths["folds"])
    contract.check_folds(folds, train)
    contract.check_predictions(contract.read_csv(fixture_paths["predictions"]), folds)


def test_leading_zeros_are_kept(fixture_paths):
    train = contract.read_csv(fixture_paths["train"])
    assert train["PERSONID"].str.len().eq(2).all()


def test_household_split_across_folds_is_rejected(fixture_paths):
    train = contract.load_modelling_table(fixture_paths["train"])
    folds = contract.read_csv(fixture_paths["folds"])
    household = folds.groupby("HOUSEID").filter(lambda g: len(g) > 1)["HOUSEID"].iloc[0]
    first_trip = folds.index[folds["HOUSEID"] == household][0]
    folds.loc[first_trip, "fold"] = folds.loc[first_trip, "fold"] % contract.N_FOLDS + 1
    with pytest.raises(contract.ContractError):
        contract.check_folds(folds, train)


def test_distance_with_skip_status_is_rejected(fixture_paths):
    train = contract.read_csv(fixture_paths["train"])
    skipped = train.index[train["distance_status"] != "recorded"][0]
    train.loc[skipped, "distance_miles"] = 3.0
    with pytest.raises(contract.ContractError):
        contract.check_trip_table(train)


def test_fingerprint_ignores_order_and_duplicates():
    assert contract.train_household_fingerprint(["B", "A", "A"]) == \
        contract.train_household_fingerprint(["A", "B"])


def test_missing_prediction_is_rejected(fixture_paths):
    folds = contract.read_csv(fixture_paths["folds"])
    predictions = contract.read_csv(fixture_paths["predictions"]).iloc[1:]
    with pytest.raises(contract.ContractError):
        contract.check_predictions(pd.DataFrame(predictions), folds)

"""Baseline and models (owner: Galvin).

    python -m src.models             # real Train table and folds
    python -m src.models --fixture   # fake data

Goal: for every model, an out-of-fold prediction for every trip in folds.csv, written to
outputs/predictions/predictions.csv (CONTRACT.md, section 6). Suggested order:
1. baseline_median   (required) - median duration of the fit rows in each fold
2. median_regression (required) - quantile 0.5
3. a tree model with a median (quantile 0.5) objective
4. gamma_regression  (log link; estimates the conditional mean; fit on positive targets)
Imputation, encoding and scaling must be learned inside each fold's fit rows only.
"""

import argparse

import pandas as pd

from src import contract
from src.paths import output_paths


def predict_out_of_fold(modelling_train: pd.DataFrame, folds: pd.DataFrame) -> pd.DataFrame:
    """Return predictions with columns TDCASEID, fold, model, prediction_min."""
    raise NotImplementedError("Galvin: implement predict_out_of_fold(), starting with the baseline")


def main(fixture: bool) -> None:
    paths = output_paths(fixture)
    train = contract.load_modelling_table(paths["train"])
    folds = contract.read_csv(paths["folds"])
    contract.check_folds(folds, train)
    predictions = predict_out_of_fold(train, folds)
    contract.check_predictions(predictions, folds)
    paths["predictions"].parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(paths["predictions"], index=False)
    print(predictions.groupby("model").size())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", action="store_true", help="use the fake data in outputs/fixture")
    main(parser.parse_args().fixture)

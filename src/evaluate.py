"""Scoring (owner: Anthony).

    python -m src.evaluate             # real predictions
    python -m src.evaluate --fixture   # fake data

Goal: score out-of-fold predictions with the metrics fixed in CONTRACT.md, section 7,
and write outputs/evaluation/metrics.csv. Check first with a hand-worked example:
actual [10, 20, 30] and prediction [15, 20, 25] give MAE = 10/3 minutes.
"""

import argparse

import pandas as pd

from src import contract
from src.paths import output_paths


def score(predictions: pd.DataFrame, modelling_train: pd.DataFrame) -> pd.DataFrame:
    """Return one row per model (and per subgroup) with n_trips and the metrics."""
    raise NotImplementedError("Anthony: implement score()")


def main(fixture: bool) -> None:
    paths = output_paths(fixture)
    train = contract.load_modelling_table(paths["train"])
    folds = contract.read_csv(paths["folds"])
    predictions = contract.read_csv(paths["predictions"])
    contract.check_folds(folds, train)
    contract.check_predictions(predictions, folds)
    metrics = score(predictions, train)
    paths["metrics"].parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(paths["metrics"], index=False)
    print(metrics)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", action="store_true", help="use the fake data in outputs/fixture")
    main(parser.parse_args().fixture)

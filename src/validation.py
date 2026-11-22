"""Household-grouped folds (owner: Anthony).

    python -m src.validation             # real Train table
    python -m src.validation --fixture   # fake data

Goal: assign every modelling Train row to one of 5 folds by HOUSEID and write
outputs/validation/folds.csv (CONTRACT.md, section 5). Use the Train table only.
"""

import argparse

import pandas as pd

from src import contract
from src.paths import output_paths


def make_folds(modelling_train: pd.DataFrame, n_folds: int = contract.N_FOLDS) -> pd.DataFrame:
    """Return a DataFrame with columns TDCASEID, HOUSEID, fold (1..n_folds)."""
    raise NotImplementedError("Anthony: implement make_folds(), e.g. with sklearn GroupKFold")


def main(fixture: bool) -> None:
    paths = output_paths(fixture)
    train = contract.load_modelling_table(paths["train"])
    folds = make_folds(train)
    contract.check_folds(folds, train)
    paths["folds"].parent.mkdir(parents=True, exist_ok=True)
    folds.to_csv(paths["folds"], index=False)
    print(folds.groupby("fold").agg(trips=("TDCASEID", "size"), households=("HOUSEID", "nunique")))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", action="store_true", help="use the fake data in outputs/fixture")
    main(parser.parse_args().fixture)

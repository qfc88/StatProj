"""Build small FAKE tables that follow CONTRACT.md, so each part can be tested alone.

    python -m src.make_fixture

Writes outputs/fixture/{modelling,validation,predictions}/. All IDs start with "FAKE".
Numbers from these files only test code; they never go into the report.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from src import contract
from src.paths import output_paths

MODE_CODES = {
    "car_van_suv_pickup": ["01", "02", "03", "04"],
    "public_transit": ["08", "10", "11", "12"],
    "walk": ["20"],
    "bike": ["18"],
    "other": ["07", "16", "17", "21"],
}


def _fake_trips(rng: np.random.Generator, n_households: int, first_household: int) -> pd.DataFrame:
    rows = []
    for h in range(first_household, first_household + n_households):
        house_id = f"FAKE{h:06d}"
        context = rng.choice(["urban", "rural"], p=[0.8, 0.2])
        for person in range(1, rng.integers(1, 3) + 1):
            status = rng.choice(["recorded", "appropriate_skip", "not_ascertained"], p=[0.88, 0.04, 0.08])
            miles = round(float(rng.lognormal(1.6, 0.9)), 2) if status == "recorded" else np.nan
            if status == "recorded" and rng.random() < 0.02:
                miles = 0.0
            group = rng.choice(list(MODE_CODES), p=[0.9, 0.03, 0.03, 0.02, 0.02])
            for trip in range(1, rng.integers(1, 3) + 1):
                direction = "home_to_work" if trip == 1 else "work_to_home"
                speed = {"car_van_suv_pickup": 0.6, "public_transit": 0.3, "walk": 0.05,
                         "bike": 0.2, "other": 0.4}[group]
                base = (miles if miles == miles else 6.0) / speed
                duration = max(0.0, round(base + rng.normal(5, 6) / 5) * 5)
                if rng.random() < 0.01:
                    duration = np.nan                      # not ascertained
                rows.append({
                    "TDCASEID": f"{house_id}{person:02d}{trip:02d}",
                    "HOUSEID": house_id,
                    "PERSONID": f"{person:02d}",
                    "duration_min": duration,
                    "distance_miles": miles,
                    "distance_status": status,
                    "trptrans_code": rng.choice(MODE_CODES[group]),
                    "mode_group": group,
                    "in_main_scope": group != "other",
                    "departure_minute": int(rng.integers(5 * 60, 9 * 60) if trip == 1
                                            else rng.integers(15 * 60, 19 * 60)),
                    "direction": direction,
                    "residential_context": context,
                    "trip_weight": round(float(rng.uniform(1e6, 3e7)), 2),
                })
    return pd.DataFrame(rows, columns=contract.TRIP_COLUMNS)


def build_fixture(paths: dict, seed: int = 0) -> None:
    """Write fake train/test tables, fake folds and two fake prediction sets."""
    rng = np.random.default_rng(seed)
    train = _fake_trips(rng, n_households=80, first_household=1)
    test = _fake_trips(rng, n_households=20, first_household=81)
    for frame, name in [(train, "train"), (test, "test")]:
        contract.check_trip_table(frame, name=f"fixture {name}")
    contract.check_households_separate(train, test)

    # Fake folds: households taken in order and assigned 1..5 in turn.
    # This only stands in for Anthony's real fold assignment.
    modelling_train = contract.modelling_rows(train)
    households = sorted(modelling_train["HOUSEID"].unique())
    fold_of = {h: i % contract.N_FOLDS + 1 for i, h in enumerate(households)}
    folds = modelling_train[["TDCASEID", "HOUSEID"]].assign(fold=modelling_train["HOUSEID"].map(fold_of))
    contract.check_folds(folds, modelling_train)

    # Two fake prediction sets so the scoring code can be tested before real models exist.
    constant = folds[["TDCASEID", "fold"]].assign(model="fake_constant_20", prediction_min=20.0)
    noisy = folds[["TDCASEID", "fold"]].assign(
        model="fake_noisy_truth",
        prediction_min=(modelling_train["duration_min"].to_numpy()
                        + rng.normal(0, 5, len(folds))).clip(min=0).round(1),
    )
    predictions = pd.concat([constant, noisy], ignore_index=True)[contract.PREDICTION_COLUMNS]
    contract.check_predictions(predictions, folds)

    outputs = {"train": train, "test": test, "folds": folds, "predictions": predictions}
    for key, frame in outputs.items():
        Path(paths[key]).parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(paths[key], index=False)
    print(f"Fixture written: {len(train)} train trips ({len(modelling_train)} modelling rows), "
          f"{len(test)} test trips, {len(predictions)} prediction rows.")
    print("These are FAKE data for testing code only.")


if __name__ == "__main__":
    build_fixture(output_paths(fixture=True))

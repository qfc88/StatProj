"""Project paths. Every script builds its paths from here; do not hard-code absolute paths."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "Data"          # raw NHTS files (capital D)
OUTPUT_DIR = PROJECT_ROOT / "outputs"     # generated files, not committed

TRIP_CSV = DATA_DIR / "tripv2pub.csv"
PERSON_CSV = DATA_DIR / "perv2pub.csv"
CODEBOOK_XLSX = DATA_DIR / "NHTS_2022_Codebook_V2.1.xlsx"


def output_paths(fixture: bool = False) -> dict:
    """File locations for the real outputs, or for the fake fixture when ``fixture=True``."""
    root = OUTPUT_DIR / "fixture" if fixture else OUTPUT_DIR
    return {
        "train": root / "modelling" / "train.csv",
        "test": root / "modelling" / "test.csv",
        "folds": root / "validation" / "folds.csv",
        "predictions": root / "predictions" / "predictions.csv",
        "metrics": root / "evaluation" / "metrics.csv",
    }

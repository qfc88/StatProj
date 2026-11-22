"""Project status: what exists, what is pending, and the next step for each member.

    python -m src.status                 # whole team
    python -m src.status --name Jovie    # one member

AI assistants run this at the start of every session (AGENTS.md, section 1) so that
advice is based on the real state of the repository, not on guesses.
Outputs in outputs/ are local: each person rebuilds them on their own computer.
"""

import argparse
import ast
import subprocess

from src import contract
from src.paths import DATA_DIR, PROJECT_ROOT, output_paths

PARTS = {
    "prepare_data": ("galvin", "src/prepare_data.py", "build_modelling_tables"),
    "make_folds": ("anthony", "src/validation.py", "make_folds"),
    "models": ("jovie", "src/models.py", "predict_out_of_fold"),
    "score": ("anthony", "src/evaluate.py", "score"),
}
DATA_FILES = ["hhv2pub.csv", "perv2pub.csv", "tripv2pub.csv", "vehv2pub.csv", "ldtv2pub.csv",
              "NHTS_2022_Codebook_V2.1.xlsx", "NHTS_2022_Data_Dictionary_V2.1.xlsx", "Citation.pdf"]


def is_implemented(path, function_name) -> bool:
    """False while the function still raises NotImplementedError (the starting stub)."""
    tree = ast.parse((PROJECT_ROOT / path).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            for inner in ast.walk(node):
                if isinstance(inner, ast.Raise) and "NotImplementedError" in ast.unparse(inner):
                    return False
            return True
    return False


def _git(*args) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=20)
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def git_state() -> dict:
    changed = [line for line in _git("status", "--porcelain").splitlines() if line.strip()]
    unpushed = _git("rev-list", "--count", "@{u}..HEAD")
    return {
        "branch": _git("branch", "--show-current") or "(unknown)",
        "uncommitted_files": len(changed),
        "unpushed_commits": int(unpushed) if unpushed.isdigit() else None,
        "has_upstream": bool(_git("rev-parse", "--abbrev-ref", "@{u}")),
        "last_commit": _git("log", "-1", "--format=%h %s (%cr)"),
    }


def _mtime(path):
    return path.stat().st_mtime if path.exists() else None


def output_state(fixture: bool) -> dict:
    """Existence, validity and freshness of each output file."""
    paths = output_paths(fixture)
    state = {"paths": paths, "problems": []}
    train = test = folds = None
    try:
        if paths["train"].exists() and paths["test"].exists():
            train_all = contract.read_csv(paths["train"])
            test_all = contract.read_csv(paths["test"])
            contract.check_trip_table(train_all, "train")
            contract.check_trip_table(test_all, "test")
            contract.check_households_separate(train_all, test_all)
            train = contract.modelling_rows(train_all)
            state["train_trips"], state["test_trips"] = len(train_all), len(test_all)
            state["modelling_rows"] = len(train)
            state["fingerprint_ok"] = (contract.train_household_fingerprint(train_all["HOUSEID"])
                                       == contract.EXPECTED_TRAIN_HOUSEHOLD_SHA256)
        if train is not None and paths["folds"].exists():
            folds = contract.read_csv(paths["folds"])
            contract.check_folds(folds, train)
            state["folds_ok"] = True
        if folds is not None and paths["predictions"].exists():
            predictions = contract.read_csv(paths["predictions"])
            contract.check_predictions(predictions, folds)
            state["models"] = sorted(predictions["model"].unique())
        state["metrics_exists"] = paths["metrics"].exists()
    except contract.ContractError as error:
        state["problems"].append(str(error).splitlines()[0])
    # A later file older than the file it was built from must be rebuilt.
    order = ["train", "folds", "predictions", "metrics"]
    for earlier, later in zip(order, order[1:]):
        t_earlier, t_later = _mtime(paths[earlier]), _mtime(paths[later])
        if t_earlier and t_later and t_later < t_earlier:
            state["problems"].append(f"{later} is older than {earlier}: rebuild {later}")
    return state


def pending_items(done: dict, real: dict) -> dict:
    """Next step per member, based on code and real outputs."""
    expected = {"train_trips": 3516, "test_trips": 877, "modelling_rows": 3484}
    steps = {"galvin": [], "anthony": [], "jovie": []}
    has_train = "train_trips" in real
    counts_ok = has_train and all(real.get(k) == v for k, v in expected.items()) and real.get("fingerprint_ok")

    if not done["prepare_data"]:
        steps["galvin"].append("Write build_modelling_tables() in src/prepare_data.py (docs/team/galvin.md).")
    elif not has_train:
        steps["galvin"].append("Run: python -m src.prepare_data")
    elif not counts_ok:
        steps["galvin"].append(
            f"STOP: counts or fingerprint differ from CONTRACT.md (train {real.get('train_trips')}, "
            f"test {real.get('test_trips')}, modelling {real.get('modelling_rows')}, "
            f"fingerprint ok: {real.get('fingerprint_ok')}). Report to the team; do not change rules to match.")
    else:
        steps["galvin"].append("Done for real data. Open/finish the pull request and review Jovie's work.")

    if not done["make_folds"]:
        steps["anthony"].append("Write make_folds() in src/validation.py; test with --fixture.")
    elif not has_train:
        steps["anthony"].append("Waiting for real train.csv (Galvin). Meanwhile test with: python -m src.validation --fixture")
    elif not real.get("folds_ok"):
        steps["anthony"].append("Run: python -m src.validation   (real folds)")
    if not done["score"]:
        steps["anthony"].append("Write score() in src/evaluate.py; check MAE of [10,20,30] vs [15,20,25] = 10/3.")
    elif real.get("models") and not real.get("metrics_exists"):
        steps["anthony"].append("Run: python -m src.evaluate   (score real predictions)")

    if not done["models"]:
        steps["jovie"].append("Write predict_out_of_fold() in src/models.py, starting with baseline_median; test with --fixture.")
    elif not real.get("folds_ok"):
        steps["jovie"].append("Waiting for real folds.csv (Anthony). Meanwhile test with: python -m src.models --fixture")
    elif not real.get("models"):
        steps["jovie"].append("Run: python -m src.models   (real out-of-fold predictions)")
    else:
        missing = {"baseline_median", "median_regression"} - set(real["models"])
        if missing:
            steps["jovie"].append(f"Required models not in predictions yet: {sorted(missing)}")
    return steps


def main(name=None) -> None:
    member = (name or "").strip().lower()
    print("=" * 70)
    print("StatProj status" + (f" for {name}" if name else ""))
    print("=" * 70)

    git = git_state()
    print(f"Git branch: {git['branch']} | uncommitted files: {git['uncommitted_files']} | "
          f"unpushed commits: {git['unpushed_commits'] if git['has_upstream'] else 'no upstream yet'}")
    print(f"Last commit: {git['last_commit']}")
    if git["branch"] == "main":
        print("  -> You are on main. Create your own branch before editing (docs/WORKFLOW_GIT.md, step 3).")

    missing_data = [f for f in DATA_FILES if not (DATA_DIR / f).exists()]
    print("Data/: " + ("all 8 files present" if not missing_data else f"MISSING {missing_data}"))

    done = {part: is_implemented(path, fn) for part, (_, path, fn) in PARTS.items()}
    print("\nCode (written = no longer a stub):")
    for part, (owner, path, fn) in PARTS.items():
        print(f"  {owner:8s} {path + '::' + fn:46s} {'written' if done[part] else 'stub (not written yet)'}")

    fixture = output_state(fixture=True)
    real = output_state(fixture=False)
    print("\nFake data (outputs/fixture): " + ("present" if fixture["paths"]["train"].exists()
                                              else "missing -> run: python -m src.make_fixture"))
    print("Real outputs on this computer (outputs/):")
    print(f"  train/test tables : {'%s / %s trips, %s modelling rows' % (real['train_trips'], real['test_trips'], real['modelling_rows']) if 'train_trips' in real else 'not built'}"
          + (f", fingerprint {'OK' if real['fingerprint_ok'] else 'DIFFERS'}" if 'train_trips' in real else ""))
    print(f"  folds             : {'valid' if real.get('folds_ok') else 'not built'}")
    print(f"  predictions       : {', '.join(real['models']) if real.get('models') else 'not built'}")
    print(f"  metrics           : {'present' if real.get('metrics_exists') else 'not built'}")
    for problem in fixture["problems"] + real["problems"]:
        print(f"  PROBLEM: {problem}")

    steps = pending_items(done, real)
    print("\nPending / next steps:")
    for who in ([member] if member in steps else steps):
        for step in steps[who] or ["Nothing pending in code; review a teammate's pull request."]:
            print(f"  {who.capitalize():8s} {step}")
    if member and member not in steps:
        print(f"  Name '{name}' is not in docs/team/README.md. Ask which part this member works on.")
    print("\nReminders: Test stays locked until the chosen model is written down. "
          "Fixture numbers are fake. Never change a rule to match a number.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", help="team nickname, e.g. Galvin, Jovie, Anthony")
    main(parser.parse_args().name)

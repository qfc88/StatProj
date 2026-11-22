#!/usr/bin/env bash
# One-time setup for macOS and Linux:  bash setup.sh
# Creates .venv, installs requirements.txt, builds the fake fixture and runs the checks.
set -euo pipefail
cd "$(dirname "$0")"

echo "== StatProj setup =="
PYTHON=""
for candidate in python3.12 python3.13 python3.11 python3.10 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        version="$("$candidate" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true)"
        case "$version" in
            3.10|3.11|3.12|3.13) PYTHON="$candidate"; break ;;
        esac
    fi
done
if [ -z "$PYTHON" ]; then
    echo "Python 3.10-3.13 was not found. Install Python 3.12 from https://www.python.org/downloads/ and run this script again."
    exit 1
fi
echo "Using $PYTHON ($("$PYTHON" --version))"

if [ ! -x ".venv/bin/python" ]; then
    echo "Creating the virtual environment in .venv ..."
    "$PYTHON" -m venv .venv
fi
VENV_PYTHON=".venv/bin/python"

echo "Installing libraries (this can take a few minutes) ..."
"$VENV_PYTHON" -m pip install --upgrade pip --quiet
"$VENV_PYTHON" -m pip install -r requirements.txt --quiet

missing=""
for f in hhv2pub.csv perv2pub.csv tripv2pub.csv vehv2pub.csv ldtv2pub.csv \
         NHTS_2022_Codebook_V2.1.xlsx NHTS_2022_Data_Dictionary_V2.1.xlsx Citation.pdf; do
    [ -f "Data/$f" ] || missing="$missing $f"
done
if [ -n "$missing" ]; then
    echo "Missing data files in Data/:$missing. Tell the team."
else
    echo "All 8 data files are present in Data/."
fi

echo "Building the fake test data and running the checks ..."
"$VENV_PYTHON" -m src.make_fixture
"$VENV_PYTHON" -m pytest -q

echo ""
echo "Setup finished."
echo "Each time you open a new terminal, activate the environment with:  source .venv/bin/activate"
echo "Next: open docs/START_HERE.md, then tell your AI assistant your name."

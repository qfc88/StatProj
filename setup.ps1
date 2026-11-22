# One-time setup for Windows.
# Run:  powershell -ExecutionPolicy Bypass -File setup.ps1   (or double-click setup.cmd)
# Creates .venv, installs requirements.txt, builds the fake fixture and runs the checks.

$ErrorActionPreference = "Continue"   # each step checks $LASTEXITCODE instead
Set-Location -Path $PSScriptRoot

function Find-Python {
    # Prefer 3.12 (the EDA version), then other supported versions.
    $candidates = @(
        @("py", "-3.12"), @("py", "-3.13"), @("py", "-3.11"), @("py", "-3.10"),
        @("python"), @("python3")
    )
    foreach ($candidate in $candidates) {
        $exe = $candidate[0]
        $pyArgs = @($candidate | Select-Object -Skip 1)
        if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
        try {
            $version = & $exe @pyArgs -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        } catch { continue }
        if ($LASTEXITCODE -eq 0 -and $version -in @("3.10", "3.11", "3.12", "3.13")) {
            return @{ Exe = $exe; Args = $pyArgs; Version = $version }
        }
    }
    return $null
}

Write-Host "== StatProj setup ==" -ForegroundColor Cyan
$python = Find-Python
if (-not $python) {
    Write-Host "Python 3.10-3.13 was not found. Install Python 3.12 from https://www.python.org/downloads/ (tick 'Add python.exe to PATH'), then run this script again." -ForegroundColor Red
    exit 1
}
Write-Host "Using Python $($python.Version)"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating the virtual environment in .venv ..."
    & $python.Exe @($python.Args) -m venv .venv
    if ($LASTEXITCODE -ne 0) { Write-Host "Could not create .venv." -ForegroundColor Red; exit 1 }
}
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

Write-Host "Installing libraries (this can take a few minutes) ..."
& $venvPython -m pip install --upgrade pip --quiet
& $venvPython -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { Write-Host "Installing the libraries failed. Copy the message above and ask the team." -ForegroundColor Red; exit 1 }

$expected = @("hhv2pub.csv", "perv2pub.csv", "tripv2pub.csv", "vehv2pub.csv", "ldtv2pub.csv",
              "NHTS_2022_Codebook_V2.1.xlsx", "NHTS_2022_Data_Dictionary_V2.1.xlsx", "Citation.pdf")
$missing = @($expected | Where-Object { -not (Test-Path (Join-Path "Data" $_)) })
if ($missing.Count -gt 0) {
    Write-Host "Missing data files in Data/: $($missing -join ', '). Tell the team." -ForegroundColor Yellow
} else {
    Write-Host "All 8 data files are present in Data/."
}

Write-Host "Building the fake test data and running the checks ..."
& $venvPython -m src.make_fixture
& $venvPython -m pytest -q
if ($LASTEXITCODE -ne 0) { Write-Host "Some checks failed. Copy the output above and ask the team." -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "Setup finished." -ForegroundColor Green
Write-Host "Each time you open a new terminal, activate the environment with:  .venv\Scripts\activate"
Write-Host "Next: open docs\START_HERE.md, then tell your AI assistant your name."

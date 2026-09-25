$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (Test-Path "$Root\.venv\Scripts\python.exe") {
  $Python = "$Root\.venv\Scripts\python.exe"
} else {
  $Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
}

$env:PYTHONPATH = if ($env:PYTHONPATH) { "$Root;$env:PYTHONPATH" } else { $Root }

& $Python -m uvicorn app.server:app --host 127.0.0.1 --port 8000

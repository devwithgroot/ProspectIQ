$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (Test-Path "$Root\.venv\Scripts\python.exe") {
  $Python = "$Root\.venv\Scripts\python.exe"
} else {
  $Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
}

& $Python -m app.pipeline @args

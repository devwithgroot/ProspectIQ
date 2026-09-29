$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (Test-Path "$Root\.venv\Scripts\python.exe") {
  $Python = "$Root\.venv\Scripts\python.exe"
} else {
  $Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
}

$env:PYTHONPATH = if ($env:PYTHONPATH) { "$Root;$env:PYTHONPATH" } else { $Root }

$Api = Start-Process -FilePath $Python -ArgumentList @(
  "-m", "uvicorn", "app.server:app",
  "--host", "127.0.0.1",
  "--port", "8000"
) -PassThru -NoNewWindow

try {
  Set-Location "$Root\web"
  if (Get-Command pnpm -ErrorAction SilentlyContinue) {
    pnpm dev --port 3000
  } else {
    npm run dev -- --port 3000
  }
} finally {
  if ($Api -and -not $Api.HasExited) {
    Stop-Process -Id $Api.Id -Force -ErrorAction SilentlyContinue
  }
  Set-Location $Root
}

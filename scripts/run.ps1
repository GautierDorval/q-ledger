Param(
  [string]$LedgerJson = "out\q-ledger.json",
  [string]$MetricsMd  = "out\metrics.md"
)

function Fail([string]$Msg) { Write-Error $Msg; exit 1 }
function Info([string]$Msg) { Write-Host $Msg -ForegroundColor Cyan }
function Ok([string]$Msg) { Write-Host $Msg -ForegroundColor Green }
function Warn([string]$Msg) { Write-Host $Msg -ForegroundColor Yellow }

function Assert-Path([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) { Fail ("Missing path: " + $Path) }
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Info ""
Info "q-ledger run (manual mode)"
Info ("Project root: " + (Get-Location))

Assert-Path "scripts\build_ledger.py"
Assert-Path "scripts\metrics.py"
Assert-Path "scripts\archive.ps1"
Assert-Path "scripts\publish.ps1"
# Config resolution
$ConfigCandidates = @("config\config.local.json","config\config.json","config\config.example.json")
$ConfigPath = $null
foreach ($c in $ConfigCandidates) {
  if (Test-Path -LiteralPath $c) { $ConfigPath = $c; break }
}
if (-not $ConfigPath) {
  Fail "No config file found. Expected one of: config\config.local.json, config\config.json, config\config.example.json"
}
$env:Q_LEDGER_CONFIG_PATH = $ConfigPath
Info ("Using config: " + $ConfigPath)

$ScopeCandidates = @("config\governance_scope.local.json","config\governance_scope.json","config\governance_scope.example.json")
$ScopePath = $null
foreach ($c in $ScopeCandidates) {
  if (Test-Path -LiteralPath $c) { $ScopePath = $c; break }
}
if ($ScopePath) {
  $env:Q_LEDGER_SCOPE_PATH = $ScopePath
  Info ("Using scope: " + $ScopePath)
} else {
  Warn "No governance scope file found. Path categorization will be limited."
}


if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
  Warn "Virtualenv not found at .venv. If you use a different venv, ensure python points to the right interpreter."
}

if (-not $env:Q_LEDGER_SALT -or $env:Q_LEDGER_SALT.Trim().Length -lt 16) {
  Warn "Q_LEDGER_SALT not found (or too short) in current session."
  Warn '  $env:Q_LEDGER_SALT="your-long-random-secret"'
  Fail "Missing Q_LEDGER_SALT in session."
}

if (-not (Test-Path -LiteralPath "input\cloudflare_logs.csv")) {
  Warn "input\cloudflare_logs.csv not found."
  Warn "Export Cloudflare Log Search CSV and place it at input\cloudflare_logs.csv"
  Fail "Missing input CSV."
}

Info ""
Info "Step 1/4 - Build ledger"
python scripts\build_ledger.py
if ($LASTEXITCODE -ne 0) { Fail "build_ledger.py failed." }
Ok "Build completed."
Assert-Path $LedgerJson

Info ""
Info "Step 2/4 - Generate metrics (legacy + q-metrics)"
python scripts\metrics.py $LedgerJson $MetricsMd
if ($LASTEXITCODE -ne 0) { Fail "metrics.py failed." }
Ok "Metrics completed."

Assert-Path "out\metrics.json"
Assert-Path "out\q-metrics.json"
Assert-Path "out\q-metrics.yml"

Info ""
Info "Step 3/4 - Archive ledger + metrics + q-metrics + CSV"
.\scripts\archive.ps1
if ($LASTEXITCODE -ne 0) { Fail "archive.ps1 failed." }
Ok "Archive completed."

Info ""
Info "Step 4/4 - Publish (clipboard assist)"
Warn "This step will pause four times for manual paste into WordPress Virtual Files."
Warn "Targets:"
Warn "  /.well-known/q-ledger.json"
Warn "  /.well-known/q-ledger.yml"
Warn "  /.well-known/q-metrics.json"
Warn "  /.well-known/q-metrics.yml"
.\scripts\publish.ps1
if ($LASTEXITCODE -ne 0) { Fail "publish.ps1 failed." }
Ok "Publish completed."

# Post-step - Update rolling 7d summary (non-blocking)
Info ""
Info "Post-step - Update summary_7d (rolling 7d)"
if (Test-Path -LiteralPath "scripts\summary_7d.py") {
  python scripts\summary_7d.py
  if ($LASTEXITCODE -ne 0) {
    Warn "summary_7d.py failed (non-blocking)."
  } else {
    Ok "summary_7d updated (out/summary_7d.md + out/summary_7d.json)."
    Assert-Path "out\summary_7d.md"
    Assert-Path "out\summary_7d.json"
  }
} else {
  Warn "scripts\summary_7d.py not found (skipped)."
}

Info ""
Info "Run completed."
Info "Outputs:"
Info ("- " + $LedgerJson)
Info ("- " + $MetricsMd)
Info "- out\q-metrics.json"
Info "- out\q-metrics.yml"
Info "Archives:"
Info "- ledgers\"
Info "- exports\"
Info ""

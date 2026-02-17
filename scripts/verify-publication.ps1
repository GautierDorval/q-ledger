# Q-Ledger — Post-publication verification
# Re-fetches public endpoints and compares canonical hashes vs local outputs.
#
# Usage:
#   .\scripts\verify-publication.ps1
#   .\scripts\verify-publication.ps1 -BaseUrl "https://example.com"
#   .\scripts\verify-publication.ps1 -ConfigPath ".\config\config.local.json"

param(
  [string]$BaseUrl = "",
  [string]$ConfigPath = ""
)

$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
  return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$repoRoot = Resolve-RepoRoot

# Prefer local config, then default config, then example
if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
  $candidates = @(
    (Join-Path $repoRoot "config\config.local.json"),
    (Join-Path $repoRoot "config\config.json"),
    (Join-Path $repoRoot "config\config.example.json")
  )

  foreach ($c in $candidates) {
    if (Test-Path $c) {
      $ConfigPath = $c
      break
    }
  }
}

if (-not (Test-Path $ConfigPath)) {
  throw "Config file not found: $ConfigPath"
}

# Venv is optional, but preferred
$pythonCandidates = @(
  (Join-Path $repoRoot ".venv\Scripts\python.exe"),
  "python"
)

$python = $null
foreach ($p in $pythonCandidates) {
  try {
    & $p --version *> $null
    $python = $p
    break
  } catch {}
}

if (-not $python) {
  throw "Python not found. Install Python 3.11+ or create .venv."
}

$scriptPath = Join-Path $repoRoot "scripts\verify_publication.py"

$argsList = @("--config", $ConfigPath)

if (-not [string]::IsNullOrWhiteSpace($BaseUrl)) {
  $argsList += @("--base-url", $BaseUrl)
}

Write-Host "Running post-publication verification..." -ForegroundColor Cyan
Write-Host "Config: $ConfigPath" -ForegroundColor DarkGray

& $python $scriptPath @argsList
if ($LASTEXITCODE -ne 0) {
  throw "Verification failed (exit code $LASTEXITCODE)."
}

Write-Host "Verification OK." -ForegroundColor Green

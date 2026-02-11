Param(
  [string]$LedgerJson = "out\q-ledger.json",
  [string]$LedgerYaml = "out\q-ledger.yml",
  [string]$MetricsMd  = "out\metrics.md",
  [string]$MetricsJson = "out\metrics.json",
  [string]$QMetricsJson = "out\q-metrics.json",
  [string]$QMetricsYaml = "out\q-metrics.yml",
  [string]$InputCsv   = "input\cloudflare_logs.csv"
)

function Assert-File([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) {
    Write-Error ("File not found: " + $Path)
    exit 1
  }
}

Assert-File $LedgerJson
Assert-File $LedgerYaml
Assert-File $MetricsMd
Assert-File $MetricsJson

# Q-metrics are expected; if missing, do not fail, but warn
$hasQMetricsJson = (Test-Path -LiteralPath $QMetricsJson)
$hasQMetricsYaml = (Test-Path -LiteralPath $QMetricsYaml)

$ledger = Get-Content -LiteralPath $LedgerJson -Raw -Encoding UTF8 | ConvertFrom-Json
$metrics = Get-Content -LiteralPath $MetricsJson -Raw -Encoding UTF8 | ConvertFrom-Json

$seq = $ledger.ledger_sequence
$gen = $ledger.generated_utc
$yyyyMMdd = $gen.Substring(0, 10)

$regime = $metrics.regime
if (-not $regime) { $regime = "unknown" }

New-Item -ItemType Directory -Force -Path "ledgers" | Out-Null
New-Item -ItemType Directory -Force -Path "exports" | Out-Null

# Archive filenames include regime tag
$dstJson = "ledgers\q-ledger-$yyyyMMdd-seq$seq-$regime.json"
$dstYaml = "ledgers\q-ledger-$yyyyMMdd-seq$seq-$regime.yml"
$dstMd   = "ledgers\metrics-$yyyyMMdd-seq$seq-$regime.md"
$dstMjs  = "ledgers\metrics-$yyyyMMdd-seq$seq-$regime.json"
$dstTag  = "ledgers\day-tag-$yyyyMMdd-seq$seq-$regime.json"

Copy-Item -LiteralPath $LedgerJson  -Destination $dstJson -Force
Copy-Item -LiteralPath $LedgerYaml  -Destination $dstYaml -Force
Copy-Item -LiteralPath $MetricsMd   -Destination $dstMd  -Force
Copy-Item -LiteralPath $MetricsJson -Destination $dstMjs -Force

# Archive q-metrics (no regime tag; tie to seq)
if ($hasQMetricsJson) {
  $dstQm = "ledgers\q-metrics-$yyyyMMdd-seq$seq.json"
  Copy-Item -LiteralPath $QMetricsJson -Destination $dstQm -Force
  Write-Host ("Archived: " + $dstQm) -ForegroundColor Green
} else {
  Write-Host "Note: out\q-metrics.json not found, q-metrics archive skipped." -ForegroundColor Yellow
}

if ($hasQMetricsYaml) {
  $dstQy = "ledgers\q-metrics-$yyyyMMdd-seq$seq.yml"
  Copy-Item -LiteralPath $QMetricsYaml -Destination $dstQy -Force
  Write-Host ("Archived: " + $dstQy) -ForegroundColor Green
} else {
  Write-Host "Note: out\q-metrics.yml not found, q-metrics YAML archive skipped." -ForegroundColor Yellow
}

# Write a compact "day tag" file
$tagObj = @{
  date_utc = $yyyyMMdd
  ledger_sequence = $seq
  regime = $regime
  rationale = $metrics.regime_rationale
  sessions_total = $metrics.sessions_total
  single_hit_ratio = $metrics.single_hit_ratio
  mean_hits_per_session = $metrics.mean_hits_per_session
  distinct_paths_total = $metrics.distinct_paths_total
  hash = $metrics.hash
  previous_hash = $metrics.previous_hash
}

($tagObj | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $dstTag -Encoding UTF8

Write-Host ("Archived: " + $dstJson) -ForegroundColor Green
Write-Host ("Archived: " + $dstYaml) -ForegroundColor Green
Write-Host ("Archived: " + $dstMd) -ForegroundColor Green
Write-Host ("Archived: " + $dstMjs) -ForegroundColor Green
Write-Host ("Archived: " + $dstTag) -ForegroundColor Green

# Archive CSV (optional)
if (Test-Path -LiteralPath $InputCsv) {
  $dstCsv = "exports\cloudflare-http-requests-$yyyyMMdd-seq$seq-$regime.csv"
  Copy-Item -LiteralPath $InputCsv -Destination $dstCsv -Force
  Write-Host ("Archived: " + $dstCsv) -ForegroundColor Green
} else {
  Write-Host "Note: input CSV not found, export archive skipped." -ForegroundColor Yellow
}

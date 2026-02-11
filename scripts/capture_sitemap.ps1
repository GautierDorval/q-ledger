Param(
  [string]$DateUtc = ""
)

function Fail([string]$Msg) { Write-Error $Msg; exit 1 }
function Info([string]$Msg) { Write-Host $Msg -ForegroundColor Cyan }
function Ok([string]$Msg) { Write-Host $Msg -ForegroundColor Green }

# Always use the same input file for C
$SourceCsv = "input\cloudflare_logs.csv"
$OutDir = "exports\C-sitemap"

if (-not (Test-Path -LiteralPath $SourceCsv)) {
  Fail "Missing input CSV: $SourceCsv"
}

if ([string]::IsNullOrWhiteSpace($DateUtc)) {
  $DateUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$dstCsv = Join-Path $OutDir ("cloudflare-sitemap-" + $DateUtc + ".csv")
Copy-Item -LiteralPath $SourceCsv -Destination $dstCsv -Force
Ok "Archived CSV: $dstCsv"

$rows = Import-Csv -LiteralPath $dstCsv
if (-not $rows -or $rows.Count -eq 0) {
  Fail "CSV contains no rows: $dstCsv"
}

$paths = $rows | Group-Object clientrequestpath | Sort-Object Count -Descending | Select-Object -First 20
$uas   = $rows | Group-Object clientrequestuseragent | Sort-Object Count -Descending | Select-Object -First 10
$codes = $rows | Group-Object edgeresponsestatus | Sort-Object Count -Descending

$minTs = ($rows | Select-Object -ExpandProperty edgestarttimestamp | Sort-Object | Select-Object -First 1)
$maxTs = ($rows | Select-Object -ExpandProperty edgestarttimestamp | Sort-Object | Select-Object -Last 1)

$uniqueIps = ($rows | Select-Object -ExpandProperty clientip | Sort-Object -Unique).Count

$summary = [ordered]@{
  type = "cloudflare_sitemap_capture"
  date_utc = $DateUtc
  source_csv = $SourceCsv
  archived_csv = $dstCsv
  rows_total = $rows.Count
  unique_ips = $uniqueIps
  window = @{
    start = $minTs
    end = $maxTs
  }
  top_paths = @(
    $paths | ForEach-Object { @{ path = $_.Name; hits = $_.Count } }
  )
  top_user_agents = @(
    $uas | ForEach-Object { @{ user_agent = $_.Name; hits = $_.Count } }
  )
  status_codes = @(
    $codes | ForEach-Object { @{ status = $_.Name; hits = $_.Count } }
  )
}

$dstJson = Join-Path $OutDir ("summary-sitemap-" + $DateUtc + ".json")
($summary | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $dstJson -Encoding UTF8
Ok "Wrote JSON: $dstJson"

$dstMd = Join-Path $OutDir ("summary-sitemap-" + $DateUtc + ".md")

$md = @()
$md += "# Cloudflare capture - sitemap"
$md += ""
$md += ("- Date (UTC): " + $DateUtc)
$md += ("- Rows: " + $rows.Count)
$md += ("- Unique IPs: " + $uniqueIps)
$md += ("- Window: " + $minTs + " -> " + $maxTs)
$md += ""
$md += "## Top paths (20)"
foreach ($p in $paths) { $md += ("- " + $p.Name + ": " + $p.Count) }
$md += ""
$md += "## Top user agents (10)"
foreach ($u in $uas) { $md += ("- " + $u.Name + ": " + $u.Count) }
$md += ""
$md += "## Status codes"
foreach ($c in $codes) { $md += ("- " + $c.Name + ": " + $c.Count) }

($md -join "`n") | Set-Content -LiteralPath $dstMd -Encoding UTF8
Ok "Wrote MD: $dstMd"

Info ""
Info "Done. C series captured from input\cloudflare_logs.csv and stored under exports\C-sitemap."
Info ""

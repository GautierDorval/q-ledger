Param(
  [string]$LedgerJson = "out\q-ledger.json",
  [string]$LedgerYaml = "out\q-ledger.yml",
  [string]$QMetricsJson = "out\q-metrics.json",
  [string]$QMetricsYaml = "out\q-metrics.yml"
)

function Assert-File([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) {
    Write-Error ("File not found: " + $Path)
    exit 1
  }
}

Assert-File $LedgerJson
Assert-File $LedgerYaml
Assert-File $QMetricsJson
Assert-File $QMetricsYaml

$ledgerJsonTxt = Get-Content -LiteralPath $LedgerJson -Raw -Encoding UTF8
$ledgerYamlTxt = Get-Content -LiteralPath $LedgerYaml -Raw -Encoding UTF8
$qmJsonTxt = Get-Content -LiteralPath $QMetricsJson -Raw -Encoding UTF8
$qmYamlTxt = Get-Content -LiteralPath $QMetricsYaml -Raw -Encoding UTF8

Write-Host ""
Write-Host "Publish (clipboard mode) - step 1/4" -ForegroundColor Cyan
Set-Clipboard -Value $ledgerJsonTxt
Write-Host "Paste now into Virtual File: /.well-known/q-ledger.json" -ForegroundColor Yellow
Read-Host "Press Enter when pasted to continue"

Write-Host ""
Write-Host "Publish (clipboard mode) - step 2/4" -ForegroundColor Cyan
Set-Clipboard -Value $ledgerYamlTxt
Write-Host "Paste now into Virtual File: /.well-known/q-ledger.yml" -ForegroundColor Yellow
Read-Host "Press Enter when pasted to continue"

Write-Host ""
Write-Host "Publish (clipboard mode) - step 3/4" -ForegroundColor Cyan
Set-Clipboard -Value $qmJsonTxt
Write-Host "Paste now into Virtual File: /.well-known/q-metrics.json" -ForegroundColor Yellow
Read-Host "Press Enter when pasted to continue"

Write-Host ""
Write-Host "Publish (clipboard mode) - step 4/4" -ForegroundColor Cyan
Set-Clipboard -Value $qmYamlTxt
Write-Host "Paste now into Virtual File: /.well-known/q-metrics.yml" -ForegroundColor Yellow
Read-Host "Press Enter when pasted to finish"

Write-Host ""
Write-Host "OK - publish completed (clipboard)." -ForegroundColor Green
Write-Host ""

Write-Host "Next recommended step: run .\scripts\verify-publication.ps1 to confirm the public endpoints match your local outputs." -ForegroundColor DarkGray

param(
  [ValidateSet('Detect','ValidateExport','ValidateCsv','Apply','All')]
  [string]$Action = 'Detect',
  [string]$Text = 'examples\ambiguous_narrative_ru.txt',
  [string]$RunDir = 'examples_out\run1',
  [string]$Csv = '',
  [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'

function Ensure-Dir($p) {
  if (-not (Test-Path -LiteralPath $p)) {
    New-Item -ItemType Directory -Path $p | Out-Null
  }
}

Ensure-Dir $RunDir

$rawJson   = Join-Path $RunDir 'candidates_raw.json'
$validJson = Join-Path $RunDir 'candidates.json'
$mapping   = Join-Path $RunDir 'mapping.json'
$reviewCsv = if ($Csv) { $Csv } else { Join-Path $RunDir 'candidates_review.csv' }
$outTxt    = Join-Path $RunDir 'out.txt'
$report    = Join-Path $RunDir 'report.json'

switch ($Action) {
  'Detect' {
    Write-Host "Step 1: detect -> $rawJson"
    & $Python -m redactru.cli detect $Text --out $rawJson
    break
  }
  'ValidateExport' {
    Write-Host "Step 2: validate+export -> $validJson, $mapping, $reviewCsv"
    & $Python -m redactru.cli validate $rawJson --out $validJson --mapping $mapping --export-csv $reviewCsv
    break
  }
  'ValidateCsv' {
    if (-not (Test-Path -LiteralPath $reviewCsv)) {
      throw "CSV not found: $reviewCsv. Provide -Csv or run ValidateExport first."
    }
    Write-Host "Step 3: validate from CSV -> $validJson, $mapping"
    & $Python -m redactru.cli validate $reviewCsv --out $validJson --mapping $mapping
    break
  }
  'Apply' {
    Write-Host "Step 4: apply -> $outTxt, $report"
    & $Python -m redactru.cli apply $Text $validJson --out $outTxt --report $report
    break
  }
  'All' {
    Write-Host "Running all steps"
    & $Python -m redactru.cli detect $Text --out $rawJson
    & $Python -m redactru.cli validate $rawJson --out $validJson --mapping $mapping --export-csv $reviewCsv
    & $Python -m redactru.cli validate $reviewCsv --out $validJson --mapping $mapping
    & $Python -m redactru.cli apply $Text $validJson --out $outTxt --report $report
    Write-Host "Done. Outputs in $RunDir"
    break
  }
  default {
    throw "Unknown action: $Action"
  }
}

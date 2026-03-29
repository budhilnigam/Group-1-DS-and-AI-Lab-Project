param(
    [Parameter(Mandatory=$true)]
    [string]$RepoName
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -Path $ScriptDir

# Path defaults to the virtual environment created in earlier steps
$PythonPath = "..\..\.venv\Scripts\python.exe"

if (-not (Test-Path $PythonPath)) {
    Write-Host "Python environment not found at $PythonPath. Ensure virtual environment is at project root!" -ForegroundColor Red
    exit 1
}

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Starting Data Extraction Pipeline for: $RepoName" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

Write-Host "`n[1/3] Running PR Extraction..." -ForegroundColor Yellow
& $PythonPath pr_extraction.py $RepoName
if ($LASTEXITCODE -ne 0) { Write-Host "Extraction failed!" -ForegroundColor Red; exit $LASTEXITCODE }

Write-Host "`n[2/3] Running AST Chunker..." -ForegroundColor Yellow
& $PythonPath ast_chunker.py $RepoName
if ($LASTEXITCODE -ne 0) { Write-Host "AST Chunking failed!" -ForegroundColor Red; exit $LASTEXITCODE }

Write-Host "`n[3/3] Running Static Filter (Linters)..." -ForegroundColor Yellow
& $PythonPath static_filter.py $RepoName
if ($LASTEXITCODE -ne 0) { Write-Host "Static filtering failed!" -ForegroundColor Red; exit $LASTEXITCODE }

Write-Host "`n=========================================" -ForegroundColor Green
Write-Host "Pipeline successfully generated the evaluation dataset!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

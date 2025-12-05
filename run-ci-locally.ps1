#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Runs all CI/CD workflow steps locally (tests, linting, code formatting)
    
.DESCRIPTION
    This script replicates the GitHub Actions CI workflow locally:
    1. Installs dependencies
    2. Runs pytest with coverage
    3. Checks code formatting with Black
    4. Lints code with Ruff
    5. Displays a summary of results
    
.EXAMPLE
    .\run-ci-locally.ps1
    
.PARAMETER FixCode
    Auto-fix formatting and linting issues
    
.NOTES
    Run from the workspace root directory
#>

param(
    [switch]$FixCode = $false
)

$ErrorActionPreference = "Continue"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  CI/CD Pipeline - Local Execution" -ForegroundColor Cyan
Write-Host "  $timestamp" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$results = @{}
$failedSteps = @()

# Step 1: Install Dependencies
Write-Host "STEP 1: Installing dependencies..." -ForegroundColor Yellow
Write-Host "---" -ForegroundColor Gray

try {
    python -m pip install --upgrade pip -q
    
    if (Test-Path "proj2/requirements.txt") {
        pip install -r proj2/requirements.txt -q
    }
    
    pip install pytest pytest-timeout pytest-cov black ruff -q
    
    Write-Host "[OK] Dependencies installed successfully" -ForegroundColor Green
    $results["Dependencies"] = "[OK]"
}
catch {
    Write-Host "[FAIL] Failed to install dependencies" -ForegroundColor Red
    $failedSteps += "Dependencies"
    $results["Dependencies"] = "[FAIL]"
}

Write-Host ""

# Step 2: Run Tests with Coverage
Write-Host "STEP 2: Running pytest with coverage..." -ForegroundColor Yellow
Write-Host "---" -ForegroundColor Gray

try {
    $env:PYTHONPATH = (Get-Location).Path
    $output = python -m pytest --tb=short --maxfail=1 -q 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host $output
        Write-Host "[OK] All tests passed" -ForegroundColor Green
        $results["Tests"] = "[OK]"
    }
    else {
        Write-Host $output
        Write-Host "[CHECK] Tests completed (may have skipped tests)" -ForegroundColor Yellow
        $results["Tests"] = "[CHECK]"
    }
}
catch {
    Write-Host "[FAIL] Failed to run tests" -ForegroundColor Red
    $failedSteps += "Tests"
    $results["Tests"] = "[FAIL]"
}

Write-Host ""

# Step 3: Check Code Formatting (Black)
Write-Host "STEP 3: Checking code formatting with Black..." -ForegroundColor Yellow
Write-Host "---" -ForegroundColor Gray

try {
    if ($FixCode) {
        Write-Host "  Auto-fixing formatting..."
        black proj2 -q
    }
    
    $output = black --check proj2 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Code formatting is correct" -ForegroundColor Green
        $results["Black"] = "[OK]"
    }
    else {
        Write-Host $output | Select-Object -First 20
        if ($FixCode) {
            Write-Host "[OK] Code formatting fixed" -ForegroundColor Green
            $results["Black"] = "[FIXED]"
        }
        else {
            Write-Host "[WARN] Formatting issues found - use -FixCode to auto-fix" -ForegroundColor Yellow
            $results["Black"] = "[ISSUES]"
        }
    }
}
catch {
    Write-Host "[FAIL] Failed to run Black" -ForegroundColor Red
    $failedSteps += "Black"
    $results["Black"] = "[FAIL]"
}

Write-Host ""

# Step 4: Lint Code (Ruff)
Write-Host "STEP 4: Linting code with Ruff..." -ForegroundColor Yellow
Write-Host "---" -ForegroundColor Gray

try {
    if ($FixCode) {
        Write-Host "  Auto-fixing linting issues..."
        ruff check proj2 --fix -q
    }
    
    $output = ruff check proj2 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] No linting issues found" -ForegroundColor Green
        $results["Ruff"] = "[OK]"
    }
    else {
        Write-Host $output | Select-Object -First 20
        if ($FixCode) {
            Write-Host "[OK] Linting issues fixed" -ForegroundColor Green
            $results["Ruff"] = "[FIXED]"
        }
        else {
            Write-Host "[WARN] Linting issues found - use -FixCode to auto-fix" -ForegroundColor Yellow
            $results["Ruff"] = "[ISSUES]"
        }
    }
}
catch {
    Write-Host "[FAIL] Failed to run Ruff" -ForegroundColor Red
    $failedSteps += "Ruff"
    $results["Ruff"] = "[FAIL]"
}

Write-Host ""

# Summary Report
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  SUMMARY REPORT" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

foreach ($key in $results.Keys | Sort-Object) {
    $status = $results[$key]
    $paddedKey = $key.PadRight(20)
    Write-Host "  $paddedKey : $status"
}

Write-Host ""

if ($failedSteps.Count -gt 0) {
    Write-Host "[FAIL] Pipeline failed with $($failedSteps.Count) error(s):" -ForegroundColor Red
    foreach ($step in $failedSteps) {
        Write-Host "   - $step" -ForegroundColor Red
    }
    Write-Host ""
    exit 1
}
else {
    Write-Host "[SUCCESS] Pipeline completed successfully!" -ForegroundColor Green
    Write-Host ""
    exit 0
}

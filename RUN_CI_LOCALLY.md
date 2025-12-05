# CI/CD Pipeline - Local Execution Script

This PowerShell script replicates the GitHub Actions CI workflow locally, allowing you to run the full test suite and code quality checks without waiting for GitHub Actions.

## Features

- ✅ Installs all required dependencies
- ✅ Runs pytest with coverage reporting
- ✅ Checks code formatting with Black
- ✅ Lints code with Ruff
- ✅ Displays a summary report
- ✅ Auto-fix code formatting and linting issues (optional)

## Usage

### Run all CI checks
```powershell
.\run-ci-locally.ps1
```

### Auto-fix formatting and linting issues
```powershell
.\run-ci-locally.ps1 -FixCode
```

## What It Does

1. **Dependencies**: Installs pytest, pytest-timeout, pytest-cov, black, and ruff
2. **Tests**: Runs the full test suite with coverage reporting
3. **Black**: Checks code formatting (or auto-fixes with `-FixCode`)
4. **Ruff**: Lints code for style issues (or auto-fixes with `-FixCode`)

## Output

The script provides a clear summary report:

```
========================================================
  SUMMARY REPORT
========================================================

  Black                : [OK]
  Dependencies         : [OK]
  Ruff                 : [ISSUES]
  Tests                : [CHECK]

[SUCCESS] Pipeline completed successfully!
```

## Exit Codes

- `0` - All checks passed or warnings only
- `1` - One or more critical failures

## Notes

- Run from the workspace root directory
- Requires Python 3.11+
- Takes approximately 2-3 minutes to complete
- The script mirrors GitHub Actions CI workflow steps

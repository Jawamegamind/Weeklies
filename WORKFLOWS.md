# GitHub Workflows Guide

## Overview

This repository has 2 GitHub Actions workflows that automate testing, code quality, documentation, and badge updates.

---

## 🔄 Workflow 1: CI Pipeline (`ci.yml`)

### Triggers
- ✅ **Push to any branch** (`push: branches: ["**"]`)
- ✅ **Pull requests to main** (`pull_request: branches: ["main"]`)

### What It Does

#### 1. **Test Execution** (with retry logic)
- Runs on: Ubuntu Latest
- Python: 3.12
- Working directory: `proj2/`
- **Excludes LLM tests** (`--ignore=tests/llm`) because:
  - Requires GPU/MPS acceleration
  - Downloads large model weights (GBs)
  - Too slow for CI environment

**Test retry strategy:**
- Max 3 attempts
- 25-minute timeout per attempt
- Logs saved as artifacts (`pytest_attempt_*.log`)

#### 2. **Code Quality Checks**
- **Black**: Auto-formats Python code
- **Ruff**: Lints and auto-fixes issues

#### 3. **Coverage Reporting**
- Generates `coverage.xml` (with branch coverage)
- Uploads to **Codecov** for visualization
- Coverage badge automatically updated by Codecov

#### 4. **Test Badge Generation**
- Parses pytest output for pass/fail counts
- Generates shields.io-compatible JSON
- Updates GitHub Gist with badge data
- Badge shows: `X passing` (green) or `X/Y passing` (red)

#### 5. **Artifact Uploads**
- Coverage XML file
- Pytest logs from all retry attempts

---

## 📚 Workflow 2: Documentation (`docs.yml`)

### Triggers
- ✅ **Push to main** (when docs-related files change)
- ✅ **Pull requests to main** (when docs-related files change)
- ✅ **Manual dispatch** (from Actions tab)

**Path filters** (only runs if these files change):
- `proj2/**`
- `scripts/**`
- `pdoc.toml`
- `.github/workflows/docs.yml`

### What It Does

#### 1. **Build API Documentation**
- Uses `pdoc` to generate API docs from Python docstrings
- Converts additional Markdown pages (via `scripts/build_docs.py`)
- Custom templates from `proj2/pdoc_templates/`
- Output: `proj2/site/`

#### 2. **Preview (PRs only)**
- Uploads `proj2/site` as downloadable artifact
- Allows reviewing docs before merge

#### 3. **Publish (main only)**
- Deploys to `gh-pages` branch
- Accessible at: `https://<username>.github.io/<repo>/`
- Uses built-in `GITHUB_TOKEN` (no extra secrets needed)

---

## 🔐 Required GitHub Secrets

### **1. `CODECOV_TOKEN`** (Required for coverage badge)
**Purpose:** Upload coverage data to Codecov

**How to get it:**
1. Go to [codecov.io](https://codecov.io)
2. Sign in with GitHub
3. Add your repository
4. Copy the "Upload Token"
5. Add to GitHub: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`
   - Name: `CODECOV_TOKEN`
   - Value: `<paste token>`

**Badge URL:**
```markdown
![Coverage](https://codecov.io/gh/<username>/<repo>/branch/main/graph/badge.svg?token=<CODECOV_TOKEN>)
```

---

### **2. `GIST_TOKEN`** (Required for test badge)
**Purpose:** Update a GitHub Gist with test results

**How to create it:**
1. Go to `Settings` → `Developer settings` → `Personal access tokens` → `Tokens (classic)`
2. Click `Generate new token (classic)`
3. Name: `Gist Token for Badge Updates`
4. Scopes: Check **`gist`** only
5. Generate and copy the token
6. Add to GitHub: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`
   - Name: `GIST_TOKEN`
   - Value: `<paste token>`

**Create the Gist:**
1. Go to [gist.github.com](https://gist.github.com)
2. Create a new gist:
   - Filename: `tests-badge.json`
   - Content: `{"schemaVersion":1,"label":"tests","message":"unknown","color":"inactive"}`
   - Make it **public**
3. Copy the Gist ID from the URL (e.g., `0c223cf33bf0cc9b91667676c415aafa`)
4. Update `ci.yml` line 109 with your Gist ID:
   ```yaml
   GIST_ID: YOUR_GIST_ID_HERE
   ```

**Badge URL:**
```markdown
![Tests](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/<username>/<gist-id>/raw/tests-badge.json)
```

---

### **3. `GITHUB_TOKEN`** (Built-in, no setup needed)
**Purpose:** Deploy docs to GitHub Pages

This is automatically provided by GitHub Actions. **No manual setup required.**

---

## 🎯 Summary of Changes Made

### ✅ Changes Applied

1. **CI workflow now runs on all branches**
   - Before: Only on PRs to main
   - After: Push to any branch + PRs to main

2. **LLM tests excluded from CI**
   - Added `--ignore=tests/llm` to all pytest commands
   - Prevents CI hanging/timeouts from model downloads
   - Run LLM tests locally with: `pytest proj2/tests/llm/`

3. **Documentation organized**
   - Created this `WORKFLOWS.md` guide
   - Documented all required secrets

### 📝 TODO: Manual Steps Required

1. **Add `CODECOV_TOKEN` secret** (see instructions above)
2. **Add `GIST_TOKEN` secret** (see instructions above)
3. **Create Gist for test badge** (see instructions above)
4. **Update Gist ID in `ci.yml`** (line 109)

---

## 🧪 Testing Locally

### Run all tests except LLM:
```bash
pytest --ignore=proj2/tests/llm
```

### Run LLM tests only (requires MPS/CUDA):
```bash
pytest proj2/tests/llm/ -v
```

### Run with coverage:
```bash
pytest --cov=proj2 --cov-report=html
# Open htmlcov/index.html to view coverage
```

### Build docs locally:
```bash
pip install pdoc markdown
python scripts/build_docs.py
# Open proj2/site/index.html
```

---

## 🔍 Monitoring

- **CI runs:** GitHub Actions tab
- **Coverage:** [codecov.io](https://codecov.io)
- **Docs:** `https://<username>.github.io/<repo>/`
- **Badges:** Add to README.md using URLs above

---

## 🐛 Troubleshooting

### "Codecov upload failed"
- Check `CODECOV_TOKEN` is set correctly
- Verify `coverage.xml` exists in artifacts

### "Gist update failed"
- Check `GIST_TOKEN` has `gist` scope
- Verify Gist ID matches in `ci.yml`
- Ensure Gist is **public**

### "Tests hang in CI"
- Confirm LLM tests are excluded (`--ignore=tests/llm`)
- Check timeout settings (currently 25min)

### "Docs not deploying"
- Enable GitHub Pages: `Settings` → `Pages` → Source: `gh-pages` branch
- Check workflow ran on `main` branch (not PR)
- Verify `GITHUB_TOKEN` has `contents: write` permission (already set)

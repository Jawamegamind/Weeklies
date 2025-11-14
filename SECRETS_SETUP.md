# 🔐 GitHub Secrets Setup - Quick Reference

## Required Secrets for Badge Updates

### 1️⃣ CODECOV_TOKEN (Coverage Badge)

**Get the token:**
1. Visit: https://codecov.io
2. Sign in with GitHub
3. Add repository: `Jawamegamind/Weeklies`
4. Copy the Upload Token

**Add to GitHub:**
```
Repository Settings → Secrets and variables → Actions → New secret
Name: CODECOV_TOKEN
Value: [paste token]
```

**Badge markdown for README:**
```markdown
![Coverage](https://codecov.io/gh/Jawamegamind/Weeklies/branch/main/graph/badge.svg?token=YOUR_CODECOV_TOKEN)
```

---

### 2️⃣ GIST_TOKEN (Test Results Badge)

**Create token:**
1. Visit: https://github.com/settings/tokens/new
2. Name: `Gist Badge Updater`
3. Scopes: ✅ **gist** (only this one)
4. Generate token and copy it

**Add to GitHub:**
```
Repository Settings → Secrets and variables → Actions → New secret
Name: GIST_TOKEN
Value: [paste token]
```

**Create the Gist:**
1. Visit: https://gist.github.com/new
2. Filename: `tests-badge.json`
3. Content: `{"schemaVersion":1,"label":"tests","message":"unknown","color":"inactive"}`
4. Create **public** gist
5. Copy Gist ID from URL (the long hex string)

**Update workflow (if needed):**
The workflow already has a Gist ID: `0c223cf33bf0cc9b91667676c415aafa`
- If this is YOUR gist → You're all set! ✅
- If this is someone else's gist → Update line 121 in `.github/workflows/ci.yml`

**Badge markdown for README:**
```markdown
![Tests](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/Jawamegamind/0c223cf33bf0cc9b91667676c415aafa/raw/tests-badge.json)
```

---

### 3️⃣ GITHUB_TOKEN (Docs Deployment)

**Setup:** ✅ **Automatic - No action required**

This token is automatically provided by GitHub Actions.

**Enable GitHub Pages:**
```
Repository Settings → Pages
Source: Deploy from a branch
Branch: gh-pages / (root)
```

Docs will be available at: `https://jawamegamind.github.io/Weeklies/`

---

## ✅ Verification Checklist

After adding secrets, verify:

- [ ] `CODECOV_TOKEN` secret exists in repository settings
- [ ] `GIST_TOKEN` secret exists in repository settings  
- [ ] Created public gist at gist.github.com
- [ ] Gist ID in ci.yml matches your gist (or kept existing)
- [ ] GitHub Pages enabled with `gh-pages` source
- [ ] Push to trigger workflows and check Actions tab
- [ ] Coverage badge updates after first successful run
- [ ] Test badge updates after first successful run

---

## 🧪 Test Without Secrets (Local)

You can run tests locally without any secrets:

```bash
# Run all tests except LLM (fast)
pytest --ignore=proj2/tests/llm

# Run with coverage report
pytest --cov=proj2 --cov-report=html
open htmlcov/index.html

# Run LLM tests (slow, requires MPS/CUDA)
pytest proj2/tests/llm/ -v
```

---

## 📊 Current Workflow Configuration

### CI Workflow
- **Triggers:** Push to any branch, PRs to main
- **Uploads:** Coverage to Codecov, test results to Gist
- **Artifacts:** pytest logs, coverage.xml

### Docs Workflow  
- **Triggers:** Push to main (docs files), PRs to main, manual
- **Builds:** API docs with pdoc + custom templates
- **Deploys:** To gh-pages branch (main only)
- **Preview:** Artifact upload on PRs

---

## 🔗 Important URLs

- **Repository:** https://github.com/Jawamegamind/Weeklies
- **Actions:** https://github.com/Jawamegamind/Weeklies/actions
- **Secrets:** https://github.com/Jawamegamind/Weeklies/settings/secrets/actions
- **Pages Settings:** https://github.com/Jawamegamind/Weeklies/settings/pages
- **Codecov:** https://app.codecov.io/gh/Jawamegamind/Weeklies
- **Gist (existing):** https://gist.github.com/Jawamegamind/0c223cf33bf0cc9b91667676c415aafa

---

## ❓ Questions?

See the full guide: `WORKFLOWS.md`

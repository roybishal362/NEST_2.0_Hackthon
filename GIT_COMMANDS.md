# Git Commands for C-TRUST Submission

## Quick Reference for Committing to GitHub

### 1. Initialize Git Repository (if not already done)

```bash
git init
```

### 2. Add All Files

```bash
git add .
```

### 3. Check Status

```bash
git status
```

This will show you all files that will be committed. Make sure:
- ✅ No `.env` files (only `.env.example`)
- ✅ No `node_modules/` directories
- ✅ No `.venv/` directories
- ✅ No sensitive data

### 4. Create Initial Commit

```bash
git commit -m "Initial commit: C-TRUST v1.0.0 - Novartis NEST 2.0 Hackathon Submission

- Multi-agent AI system for clinical trial monitoring
- 7 specialized agents + Guardian meta-agent
- Real-time DQI calculation and risk assessment
- Interactive dashboard with React/TypeScript
- Comprehensive test suite (331 tests)
- Full documentation and deployment guides"
```

### 5. Create GitHub Repository

Go to GitHub and create a new repository:
- **Name**: `c-trust` or `clinical-trial-risk-surveillance`
- **Description**: "AI-powered clinical trial monitoring system for real-time risk assessment and data quality insights"
- **Visibility**: Public (for hackathon) or Private
- **DO NOT** initialize with README, .gitignore, or license (we already have these)

### 6. Add Remote Origin

```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
```

Or with SSH:

```bash
git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO_NAME.git
```

### 7. Verify Remote

```bash
git remote -v
```

### 8. Push to GitHub

```bash
git branch -M main
git push -u origin main
```

### 9. Create Release Tag

```bash
git tag -a v1.0.0 -m "C-TRUST v1.0.0 - Novartis NEST 2.0 Hackathon Submission"
git push origin v1.0.0
```

## Verification Before Pushing

### Run Verification Script

```bash
python verify_submission.py
```

This should show:
```
✓ Repository is ready for GitHub submission!
```

### Check What Will Be Committed

```bash
git status
git diff --cached
```

### Check Ignored Files

```bash
git status --ignored
```

Make sure these are ignored:
- `.venv/`
- `node_modules/`
- `.env`
- `__pycache__/`
- `*.pyc`
- `*.log`
- `*.db`

## After Pushing to GitHub

### 1. Verify Repository on GitHub

- Check that all files are present
- Verify README displays correctly
- Check that documentation is accessible
- Ensure no sensitive data is visible

### 2. Configure Repository Settings

#### Add Topics/Tags

```
clinical-trials
ai
healthcare
risk-assessment
data-quality
fastapi
react
typescript
python
machine-learning
```

#### Update Repository Details

- Description: "AI-powered clinical trial monitoring system for real-time risk assessment and data quality insights"
- Website: (if you have a demo URL)
- Add repository image (use logo from images/)

#### Enable Features

- ✅ Issues
- ✅ Discussions (optional)
- ✅ Wiki (optional)
- ✅ Projects (optional)

### 3. Create GitHub Release

Go to Releases → Create a new release:

- **Tag**: v1.0.0
- **Title**: C-TRUST v1.0.0 - Novartis NEST 2.0 Hackathon Submission
- **Description**:

```markdown
# C-TRUST v1.0.0

AI-powered Clinical Trial Risk & Uncertainty Surveillance Tool

## 🎯 Highlights

- 7 specialized AI agents for comprehensive trial monitoring
- Guardian meta-agent for consensus-based decision making
- Real-time Data Quality Index (DQI) calculation
- Interactive dashboard with multiple views
- 331 automated tests (unit, integration, property-based)
- Production-ready with comprehensive documentation

## 📦 What's Included

- Complete source code
- Comprehensive test suite
- Interactive React/TypeScript dashboard
- FastAPI backend
- Full documentation
- Deployment guides
- Submission materials

## 🚀 Quick Start

See [SETUP.md](SETUP.md) for installation instructions.

## 📚 Documentation

- [README](README.md) - Project overview
- [SIMPLE_EXPLANATION](c_trust/SIMPLE_EXPLANATION.md) - High-level overview
- [TECHNICAL_DOCUMENTATION](c_trust/TECHNICAL_DOCUMENTATION.md) - Architecture details
- [VIDEO_SCRIPT](c_trust/VIDEO_SCRIPT.md) - Presentation script

## 🏆 Hackathon Submission

This project was developed for the Novartis NEST 2.0 Hackathon.

All submission materials are in the `submission/` directory.
```

### 4. Update README Badges (Optional)

Add badges to your README:

```markdown
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![React](https://img.shields.io/badge/React-18+-blue.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5+-blue.svg)
![Tests](https://img.shields.io/badge/tests-331%20passing-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
```

## Common Git Commands

### Check Current Branch

```bash
git branch
```

### Create New Branch

```bash
git checkout -b feature-name
```

### Switch Branch

```bash
git checkout main
```

### Pull Latest Changes

```bash
git pull origin main
```

### View Commit History

```bash
git log --oneline
```

### View Changes

```bash
git diff
```

### Undo Last Commit (keep changes)

```bash
git reset --soft HEAD~1
```

### Undo Last Commit (discard changes)

```bash
git reset --hard HEAD~1
```

## Troubleshooting

### Large Files Error

If you get an error about large files:

```bash
# Check file sizes
find . -type f -size +50M

# Remove large files from git
git rm --cached path/to/large/file

# Add to .gitignore
echo "path/to/large/file" >> .gitignore
```

### Sensitive Data Committed

If you accidentally committed sensitive data:

```bash
# Remove file from git history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/sensitive/file" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (CAUTION: This rewrites history)
git push origin --force --all
```

### Wrong Remote URL

```bash
# Check current remote
git remote -v

# Change remote URL
git remote set-url origin https://github.com/NEW_USERNAME/NEW_REPO.git
```

### Merge Conflicts

```bash
# Check status
git status

# Edit conflicted files
# Look for <<<<<<< HEAD markers

# After resolving
git add .
git commit -m "Resolved merge conflicts"
```

## Best Practices

### Commit Messages

Use clear, descriptive commit messages:

```bash
# Good
git commit -m "Add patient dashboard with timeline view"
git commit -m "Fix DQI calculation for edge cases"
git commit -m "Update documentation with deployment guide"

# Bad
git commit -m "fix"
git commit -m "update"
git commit -m "changes"
```

### Commit Frequency

- Commit often with logical changes
- Each commit should be a complete, working change
- Don't commit broken code

### Branch Strategy

- `main` - Production-ready code
- `develop` - Development branch
- `feature/*` - Feature branches
- `bugfix/*` - Bug fix branches

### Before Pushing

Always:
1. Run tests: `pytest`
2. Run verification: `python verify_submission.py`
3. Check status: `git status`
4. Review changes: `git diff`

## GitHub Actions (Optional)

Create `.github/workflows/ci.yml` for automated testing:

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest
```

## Final Checklist

Before pushing to GitHub:

- [ ] Run `python verify_submission.py` - should pass 100%
- [ ] Check `git status` - no unexpected files
- [ ] Review `.gitignore` - all patterns correct
- [ ] No `.env` files committed
- [ ] No `node_modules/` committed
- [ ] No `.venv/` committed
- [ ] No sensitive data (API keys, passwords)
- [ ] All documentation is up to date
- [ ] README is comprehensive
- [ ] Tests pass: `pytest`
- [ ] Commit message is descriptive

## Support

If you encounter issues:
1. Check this guide
2. Review GitHub documentation
3. Check git documentation: `git help <command>`

---

**Ready to push? Run the verification script first!**

```bash
python verify_submission.py
```

If it shows ✓ Repository is ready for GitHub submission!, you're good to go!

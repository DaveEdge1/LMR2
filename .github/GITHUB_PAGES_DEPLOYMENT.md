# GitHub Pages Deployment for LMR2 Visualizations

## Overview

This workflow automatically deploys CFR visualization results to GitHub Pages at:
**https://DaveEdge1.github.io/LMR2/**

## How It Works

The workflow has 4 jobs:
1. **Find Latest CFR Run** - Locates the most recent successful CFR analysis
2. **Download CFR Artifact** - Gets the data and flattens the directory structure
3. **Visualize** - Runs presto-viz reusable workflow (creates visualization artifact)
4. **Deploy to GitHub Pages** - Downloads visualization artifact and pushes to `gh-pages` branch

## One-Time Setup

### 1. Enable GitHub Pages

1. Go to **Settings** → **Pages**
2. Under **Source**, select:
   - Branch: **`gh-pages`**
   - Folder: **`/ (root)`**
3. Click **Save**

### 2. Verify Workflow Permissions

1. Go to **Settings** → **Actions** → **General**
2. Under **Workflow permissions**, ensure:
   - **Read and write permissions** is selected
3. Click **Save**

## Workflow Structure

```
Find Latest CFR → Download & Flatten → Visualize (Reusable) → Deploy to gh-pages
                                            ↓
                                       Artifact
                                            ↓
                                    GitHub Pages
```

### Why This Approach?

- **Separation of concerns**: Visualization and deployment are separate jobs
- **Uses working reusable workflow**: No multiprocessing issues
- **Simple deployment**: Just downloads artifact and pushes to gh-pages
- **Clean history**: Each deployment is a single commit

## Manual Deployment

If you need to manually deploy a specific visualization:

```bash
# Download artifact from GitHub Actions
gh run download <run-id> -n presto-viz-output-CFR_Run_XX_Reviz_YY

# Checkout gh-pages branch
git checkout gh-pages

# Copy files
cp -r presto-viz-output-CFR_Run_XX_Reviz_YY/* .

# Commit and push
git add .
git commit -m "Manual deployment"
git push origin gh-pages
```

## Troubleshooting

### Deployment job fails with "pathspec 'gh-pages' did not match"
The gh-pages branch doesn't exist yet. The workflow will create it on first run.

### Pages not updating
1. Check that gh-pages branch exists and has recent commits
2. Verify GitHub Pages is enabled in Settings → Pages
3. Wait a few minutes - GitHub Pages can take time to update

### Permission denied on push
Go to Settings → Actions → General → Workflow permissions and enable "Read and write permissions"

## Related Files

- Workflow: `.github/workflows/visualize.yml`
- Presto-viz fixes: `.github/PRESTO_VIZ_FIX.md`
- Patch files: `presto-viz-*.patch`

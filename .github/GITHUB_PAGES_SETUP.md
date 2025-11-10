# GitHub Pages Setup for CFR Visualization

This document explains how to configure GitHub Pages to automatically deploy your CFR visualization results using presto-viz's built-in git functionality.

## What This Does

The `visualize.yml` workflow automatically:
1. Finds the latest successful CFR run
2. Downloads the CFR data
3. Runs presto-viz scripts (1, 2, and 3) directly
4. **Script 3 automatically commits and pushes** to the `gh-pages` branch
5. GitHub Pages serves the visualization at: **https://DaveEdge1.github.io/LMR2/**

## Key Environment Variables

The workflow uses presto-viz's built-in GitHub Pages functionality via environment variables:

- **`COMMIT_VIZ_OUTPUT=true`**: Enables automatic git operations in Script 3
- **`GIT_REPO_ROOT`**: Points to the LMR2 repository root
- **`VIZ_OUTPUT_PATH=docs`**: Output directory for GitHub Pages
- **`VIZ_GIT_BRANCH=gh-pages`**: Target branch for deployment
- **`VIZ_COMMIT_MSG`**: Custom commit message with run information

## One-Time Setup Required

### Step 1: Enable GitHub Pages

1. Go to your repository: **https://github.com/DaveEdge1/LMR2**
2. Click **Settings** (top right)
3. In the left sidebar, click **Pages**
4. Under **Source**, select:
   - **Source**: `Deploy from a branch`
   - **Branch**: `gh-pages`
   - **Folder**: `/ (root)`
5. Click **Save**

### Step 2: Verify Workflow Permissions

1. In **Settings**, go to **Actions** → **General** (in left sidebar)
2. Scroll down to **Workflow permissions**
3. Ensure either:
   - **Read and write permissions** is selected, OR
   - **Read repository contents and packages permissions** is selected WITH "Allow GitHub Actions to create and approve pull requests" checked
4. Click **Save** if you made changes

## How It Works

### Workflow Flow

```
CFR Run → Download Data → Flatten Structure → Run Presto-Viz Scripts → Auto-Deploy
                                                                            ↓
                                                                       gh-pages branch
```

1. **Find Latest CFR Run**: Queries GitHub API for the latest successful run
2. **Download CFR Artifact**: Downloads the NetCDF files from that run
3. **Flatten Directory Structure**: Moves NetCDF files to root (presto-viz requirement)
4. **Checkout Repositories**: LMR2 (main) as target, presto-viz as tool
5. **Run Presto-Viz Scripts**:
   - Script 1: Format data
   - Script 2: Make maps and time series
   - Script 3: Make HTML file **AND automatically commit/push to gh-pages**

### Why This Approach?

This workflow runs presto-viz scripts **directly** instead of using the reusable workflow because:
- Script 3 has built-in git functionality that handles commits and pushes
- Setting `COMMIT_VIZ_OUTPUT=true` enables automatic deployment
- No need for separate download/commit steps
- Simpler and more maintainable

### Accessing Your Visualization

Once deployed, your visualization will be available at:
- **Main URL**: https://DaveEdge1.github.io/LMR2/
- This automatically redirects to the main visualization HTML file

### Automatic Updates

The workflow can run:
- **Manually**: Click "Run workflow" in Actions tab
- **Scheduled**: Daily at midnight UTC (configured in workflow)
- **On demand**: Trigger via workflow_dispatch

## Directory Structure

After deployment, the `gh-pages` branch will contain:

```
gh-pages/
├── index.html              # Auto-generated redirect to main viz
├── [visualization].html    # Main interactive visualization
├── *.png                   # Generated map images
├── *.html                  # Time series plots
├── README.md              # Deployment info
└── [other assets]         # CSS, JS, etc.
```

## Troubleshooting

### Pages not deploying

1. Check **Actions** tab for failed workflows
2. Verify `gh-pages` branch exists after first successful run
3. Check **Settings** → **Pages** shows "Your site is published at..."

### Permissions errors

If you see errors like "refusing to allow a GitHub App to create or update workflow":
1. Go to **Settings** → **Actions** → **General**
2. Under **Workflow permissions**, select **Read and write permissions**
3. Save and re-run the workflow

### Visualization not loading

1. Check that the artifact `presto-viz-output-*` was created in the visualize job
2. Verify the download step finds files: check logs for "Contents of docs directory"
3. Ensure the HTML files are valid (not error pages)

## Manual Deployment

If you need to manually deploy a specific visualization:

```bash
# Clone the repository
git clone https://github.com/DaveEdge1/LMR2.git
cd LMR2

# Create/checkout gh-pages branch
git checkout --orphan gh-pages

# Copy your visualization files
cp -r /path/to/visualization/output/* .

# Commit and push
git add .
git commit -m "Manual deployment of visualization"
git push origin gh-pages
```

## How Script 3 Handles Deployment

When `COMMIT_VIZ_OUTPUT=true`, Script 3 (`3_make_html_file.py`) automatically:

1. Copies output to `VIZ_OUTPUT_PATH` (defaults to `docs/`)
2. Switches to `VIZ_GIT_BRANCH` (defaults to `gh-pages`)
3. Commits all changes with `VIZ_COMMIT_MSG`
4. Pushes to remote

This all happens transparently within Script 3, so you don't need separate deployment steps!

## Customization

### Change Deployment Branch

To deploy to `main` branch instead of `gh-pages`:

```yaml
env:
  VIZ_GIT_BRANCH: 'main'  # Change from 'gh-pages' to 'main'
```

Then in **Settings** → **Pages**, select `main` branch and `/docs` folder.

### Change Output Directory

To use a different directory (e.g., `public/`):

```yaml
env:
  VIZ_OUTPUT_PATH: 'public'  # Change from 'docs' to 'public'
```

### Change Deployment Frequency

Edit `.github/workflows/visualize.yml` line 6:

```yaml
schedule:
  - cron: '0 0 * * *'  # Daily at midnight
  # - cron: '0 */6 * * *'  # Every 6 hours
  # - cron: '0 12 * * 1'   # Weekly on Monday at noon
```

### Custom Domain

To use a custom domain (e.g., `viz.yourdomain.com`):

1. Add a `CNAME` file to the `gh-pages` branch with your domain
2. Configure DNS at your domain provider
3. See: https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site

## Comparison: Direct vs Reusable Workflow

### Direct Approach (Current)
✅ Uses presto-viz's built-in git functionality
✅ Simpler workflow with fewer steps
✅ Script 3 handles everything automatically
✅ Single job does visualization + deployment

### Reusable Workflow Approach (Previous)
- Calls presto-viz reusable workflow
- Downloads artifacts afterward
- Manually commits and pushes
- Requires separate deployment job

## Related Files

- **Workflow**: `.github/workflows/visualize.yml`
- **Presto-viz fixes**: `.github/PRESTO_VIZ_FIX.md`
- **Patches**: `presto-viz-*.patch`

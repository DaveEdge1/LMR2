# GitHub Pages Setup for CFR Visualization

This document explains how to configure GitHub Pages to automatically deploy your CFR visualization results.

## What This Does

The `visualize.yml` workflow now automatically:
1. Finds the latest successful CFR run
2. Downloads the CFR data
3. Generates interactive visualizations using presto-viz
4. Deploys the visualization to GitHub Pages at: **https://DaveEdge1.github.io/LMR2/**

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
CFR Run → Download Data → Flatten Structure → Presto-Viz → Deploy to gh-pages
```

1. **Find Latest CFR Run**: Queries GitHub API for the latest successful run
2. **Download CFR Artifact**: Downloads the NetCDF files from that run
3. **Flatten Directory Structure**: Moves NetCDF files to root (presto-viz requirement)
4. **Generate Visualization**: Calls presto-viz reusable workflow
5. **Deploy to GitHub Pages**: Downloads visualization output and pushes to `gh-pages` branch

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

## Customization

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

## Related Files

- **Workflow**: `.github/workflows/visualize.yml`
- **Presto-viz fixes**: `.github/PRESTO_VIZ_FIX.md`
- **Patches**: `presto-viz-*.patch`

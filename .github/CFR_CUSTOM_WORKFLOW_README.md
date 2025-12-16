# CFR Custom Data Workflow Guide

## Overview

The `cfr-custom.yml` workflow automates the process of running Climate Field Reconstruction (CFR) analysis with custom LiPD (Linked Paleo Data) proxy data.

## How It Works

### Workflow Steps

1. **Extract Data URL** - Reads `lipd_data_url` from `lmr_configs.yml`
2. **Download LiPD File** - Downloads the source `lipd.pkl` file from the configured URL
3. **Convert Format** - Runs `convert_lipd_to_cfr_dataframe.py` to convert LiPD format to CFR-compatible DataFrame pickle
4. **Run CFR Analysis** - Executes CFR reconstruction using the converted data in Docker container
5. **Upload Results** - Saves reconstruction outputs and converted data as artifacts

### Data Flow

```
lmr_configs.yml (lipd_data_url)
    ↓
Download lipd.pkl from URL
    ↓
convert_lipd_to_cfr_dataframe.py
    ↓
lipd_cfr.pkl (DataFrame pickle)
    ↓
Mount into Docker container
    ↓
CFR Analysis (cfr_main_code.py)
    ↓
Reconstruction outputs in ./recons/
```

## Configuration

### 1. Update `lmr_configs.yml`

Specify your custom LiPD data URL:

```yaml
# For custom LiPD data: specify the URL to download the source lipd.pkl file
lipd_data_url: https://github.com/DaveEdge1/LMR2/raw/refs/heads/main/lipd.pkl

# Path to proxy database inside Docker container
proxydb_path: /app/lipd_cfr.pkl
```

**Supported URL formats:**
- GitHub raw URLs: `https://github.com/USER/REPO/raw/refs/heads/BRANCH/lipd.pkl`
- GitHub releases: `https://github.com/USER/REPO/releases/download/TAG/lipd.pkl`
- Direct URLs: Any publicly accessible URL to a LiPD pickle file

### 2. Ensure Conversion Script Exists

The workflow requires `convert_lipd_to_cfr_dataframe.py` in the repository root.

## Running the Workflow

### Automatic Triggers

The workflow runs automatically when:
- The Docker build workflow completes successfully
- You push changes to: `cfr_main_code.py`, `lmr_configs.yml`, or `convert_lipd_to_cfr_dataframe.py`

### Manual Trigger

1. Go to **Actions** tab in GitHub
2. Select **"Run CFR with custom LiPD data"**
3. Click **"Run workflow"**
4. Select branch (usually `main`)
5. Click **"Run workflow"**

## Expected Outputs

### Artifacts

1. **`cfr-custom-results-{run_number}`** (30 day retention)
   - Reconstruction NetCDF files from `./recons/`
   - Contains temperature field reconstructions, ensemble statistics, etc.

2. **`lipd-cfr-converted-{run_number}`** (7 day retention)
   - The converted `lipd_cfr.pkl` DataFrame pickle
   - Useful for debugging or reusing the converted data

### Reconstruction Files

Located in `./recons/test-run-da-cfg/`:
- NetCDF files with reconstructed climate fields
- Ensemble statistics
- Proxy metadata

## Troubleshooting

### Error: "lipd_data_url not found in lmr_configs.yml"

**Solution**: Add the `lipd_data_url` parameter to `lmr_configs.yml`:

```yaml
lipd_data_url: https://your-url-here/lipd.pkl
```

### Error: "Downloaded file is empty"

**Causes:**
- URL is incorrect or inaccessible
- File requires authentication (not publicly accessible)
- Network issues

**Solution:**
- Verify the URL is publicly accessible
- Test the URL in a browser
- Check if the file requires authentication
- Use a different hosting location (GitHub Releases, etc.)

### Error: Conversion fails with "missing data or extraction failed"

**Causes:**
- LiPD file structure is incompatible
- Missing required fields (time, value data)

**Solution:**
- Check conversion output for specific proxy errors
- Verify your LiPD file has the expected structure:
  ```python
  {'D': {proxy_id: {'paleoData': {...}, 'geo': {...}}, ...}}
  ```
- Review `convert_lipd_to_cfr_dataframe.py` for field mapping

### Error: "ProxyDatabase has no records" or "0 proxies loaded"

**Causes:**
- Converted DataFrame is empty
- Column names don't match CFR expectations
- File path is incorrect

**Solution:**
- Check the "Convert LiPD" step output for number of extracted proxies
- Verify `proxydb_path: /app/lipd_cfr.pkl` in config matches Docker mount
- Review conversion logs for skipped proxies

### Error: CFR analysis fails during reconstruction

**Causes:**
- Insufficient memory
- Incompatible proxy types
- Configuration issues

**Solution:**
- Check swap space is enabled (workflow does this automatically)
- Review `filter_proxydb_kwargs` to ensure proxy types are supported
- Reduce `nens` (ensemble size) if memory is an issue
- Check prior/observation data URLs are accessible

## Customization

### Using Different LiPD Sources

To use a different LiPD dataset:

1. Upload your `lipd.pkl` file to:
   - GitHub repository (commit to main or create a release)
   - Public file hosting service
   - Your own server

2. Update `lipd_data_url` in `lmr_configs.yml`:
   ```yaml
   lipd_data_url: https://your-server.com/path/to/custom-lipd.pkl
   ```

3. Workflow will automatically download and convert it

### Modifying Conversion Logic

If your LiPD file has a different structure:

1. Edit `convert_lipd_to_cfr_dataframe.py`
2. Update the `extract_proxy_data()` function
3. Test locally first:
   ```bash
   python convert_lipd_to_cfr_dataframe.py your-lipd.pkl output.pkl
   ```
4. Push changes - workflow will use updated script

### Filtering Proxies

Update `filter_proxydb_kwargs` in `lmr_configs.yml`:

```yaml
filter_proxydb_kwargs:
  by: ptype
  keys:
    - coral.d18O      # Only coral d18O proxies
    - coral.SrCa      # And coral Sr/Ca proxies
```

## Performance Notes

### Typical Runtime

- **Download LiPD**: 5-30 seconds (depends on file size)
- **Conversion**: 10-60 seconds (depends on number of proxies)
- **CFR Analysis**: 5-30 minutes (depends on reconstruction period, ensemble size)

### Memory Usage

- Default `nens: 10` uses ~4-6 GB memory
- Workflow creates 5 GB swap space automatically
- For larger reconstructions, consider reducing `nens` or increasing swap

### Storage

- LiPD pickle: ~2-5 MB (source file)
- Converted DataFrame: ~200 KB - 2 MB
- Reconstruction outputs: ~10-100 MB (depends on config)

## Comparison with Standard Workflow

| Feature | Standard Workflow | Custom Data Workflow |
|---------|------------------|---------------------|
| **Data Source** | PAGES2kV2.nc (built-in) | Custom LiPD pickle |
| **Download** | From Google Drive | From configured URL |
| **Conversion** | None (already NetCDF) | LiPD → DataFrame pickle |
| **Configuration** | `proxydb_path: /app/PAGES2kV2.nc` | `proxydb_path: /app/lipd_cfr.pkl` |
| **Workflow File** | `run-cfr.yml` | `cfr-custom.yml` |

## Example: Complete Setup

### 1. Prepare Your LiPD Data

```bash
# Option A: Commit to repository
git add my-custom-lipd.pkl
git commit -m "Add custom proxy data"
git push origin main

# Option B: Create a GitHub Release
# Go to Releases → Create new release → Attach file
```

### 2. Update Configuration

`lmr_configs.yml`:
```yaml
# Custom data URL
lipd_data_url: https://github.com/DaveEdge1/LMR2/raw/refs/heads/main/my-custom-lipd.pkl

# Where converted file will be mounted in Docker
proxydb_path: /app/lipd_cfr.pkl

# Filter to specific proxy types from your data
filter_proxydb_kwargs:
  by: ptype
  keys:
    - coral
    - tree
```

### 3. Run Workflow

- **Automatic**: Push `lmr_configs.yml` changes → workflow runs
- **Manual**: Actions tab → Run CFR with custom LiPD data → Run workflow

### 4. Download Results

1. Go to workflow run in Actions tab
2. Scroll to **Artifacts** section
3. Download `cfr-custom-results-{run_number}.zip`
4. Extract and analyze reconstruction NetCDF files

## Related Files

- **Workflow**: `.github/workflows/cfr-custom.yml`
- **Configuration**: `lmr_configs.yml`
- **Conversion Script**: `convert_lipd_to_cfr_dataframe.py`
- **Conversion Plan**: `LIPD_TO_CFR_CONVERSION_PLAN.md`
- **CFR Analysis**: `CFR_PROXY_DATA_LOADING_ANALYSIS.md`

## Support

For issues with:
- **Workflow**: Check GitHub Actions logs for error details
- **Conversion**: Review `convert_lipd_to_cfr_dataframe.py` output
- **CFR library**: See https://fzhu2e.github.io/cfr/
- **LiPD format**: See https://lipd.net/

## Version History

- **v1.0**: Initial custom data workflow with automatic LiPD conversion

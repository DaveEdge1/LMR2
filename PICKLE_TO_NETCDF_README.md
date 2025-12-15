# Converting Pickle Files to NetCDF for CFR Analysis

## Problem

The CFR library expects proxy databases in NetCDF (.nc) format, but your custom data is in Python pickle (.pkl) format. This causes the "Run CFR with custom data" workflow to fail.

## Solution

Use the provided conversion script to convert your pickle file to NetCDF format.

## Prerequisites

You need Python with these packages installed:
```bash
pip install xarray numpy pandas netCDF4
```

## Usage

### Step 1: Download your pickle file

Download the pickle file to your local machine from:
```
http://143.198.98.66:83/customRecons/17658382576189821_download/lipd.pkl
```

### Step 2: Run the conversion script

```bash
python convert_pickle_to_netcdf.py lipd.pkl lipd_cfr.nc
```

This will:
1. Load the pickle file
2. Examine its structure
3. Convert it to NetCDF format
4. Save it as `lipd_cfr.nc`
5. Verify the output

### Step 3: Upload the NetCDF file

After conversion, you need to make the NetCDF file accessible to GitHub Actions:

**Option A: Upload to your server**
Upload `lipd_cfr.nc` to your server at:
```
http://143.198.98.66:83/customRecons/test123/lipd_cfr.nc
```

**Option B: Use GitHub Releases**
1. Create a new release in your repository
2. Attach `lipd_cfr.nc` as a release asset
3. Update the workflow to download from the release URL

**Option C: Use Google Drive or Dropbox**
1. Upload to Google Drive/Dropbox
2. Get a public download link
3. Update the workflow to use that URL

### Step 4: Update the workflow

Update `.github/workflows/cfr-custom.yml` to download the `.nc` file instead of `.pkl`:

```yaml
- name: Download lipd_cfr.nc
  run: |
    python -m pip install --user gdown
    # Update this URL to wherever you uploaded the .nc file
    python -m gdown 'YOUR_NETCDF_FILE_URL' -O "${GITHUB_WORKSPACE}/lipd_cfr.nc"
```

And update the Docker mount:
```yaml
-v "${{ github.workspace }}/lipd_cfr.nc":/app/lipd_cfr.nc:ro \
```

And ensure `lmr_configs.yml` has:
```yaml
proxydb_path: /app/lipd_cfr.nc
```

## Troubleshooting

### If the conversion fails

The script will show you the structure of your pickle file. If automatic conversion fails, you may need to:

1. **Examine the structure**: Look at the output from the script showing the pickle file structure
2. **Contact the data provider**: Ask for the data in NetCDF format directly
3. **Custom conversion**: Modify the `convert_to_netcdf()` function to handle your specific data structure

### Common pickle file structures

The script handles these common formats:

1. **Already xarray.Dataset**: Direct save to NetCDF
2. **Dictionary with proxy data**: Converts to Dataset with 'proxy' dimension
3. **Custom formats**: May require manual conversion

## Example: Examining the structure

If the conversion fails, run Python interactively to examine the structure:

```python
import pickle

with open('lipd.pkl', 'rb') as f:
    data = pickle.load(f)

print(type(data))
print(dir(data))

# If it's a dictionary
if isinstance(data, dict):
    print(data.keys())
    for key in list(data.keys())[:5]:
        print(f"{key}: {type(data[key])}")
```

## Alternative: Use PAGES2kV2 Dataset

If conversion is too complex, you can revert to using the standard PAGES2kV2 dataset:

1. Change `lmr_configs.yml`:
   ```yaml
   proxydb_path: /app/PAGES2kV2.nc
   ```

2. Use the standard `run-cfr.yml` workflow instead of `cfr-custom.yml`

## Need Help?

If you encounter issues with the conversion, please provide:
1. The output from running the conversion script
2. The structure of your pickle file (first few lines)
3. Where the pickle file came from (what tool/library created it)

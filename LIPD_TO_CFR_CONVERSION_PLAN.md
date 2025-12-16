# LiPD Pickle to CFR Format Conversion Plan

## Executive Summary

After analyzing the CFR library data loading code, I've identified the **easiest path** to load your custom LiPD pickle data into CFR:

**Solution**: Convert LiPD pickle to a pandas DataFrame pickle that CFR's `from_df()` method can read directly.

---

## Background

### Current Situation

You have:
- `lipd.pkl` - 2.8 MB pickle file with 82 proxies in LiPD (Linked Paleo Data) format
- Complex nested structure: `{'D': {proxy_id: {metadata, paleoData}, ...}}`

You need:
- Format that CFR can load via `proxydb_path` in config file

### What CFR Expects

From analyzing CFR source code (`cfr/proxy.py`), the library supports:

1. **NetCDF (.nc)** → `load_nc()` → xarray.Dataset → ProxyDatabase
2. **Pickle (.pkl)** → `pd.read_pickle()` → **DataFrame** → `from_df()` → ProxyDatabase
3. **JSON/CSV** → `pd.read_json/csv()` → DataFrame → `from_df()` → ProxyDatabase

**Key Discovery**: CFR's `.pkl` support expects a **pandas DataFrame**, not raw LiPD structure!

---

## Recommended Solution: DataFrame Pickle Conversion

### Why This Is The Easiest Path

✅ **No workflow changes needed** - Just replace the pickle file
✅ **CFR already supports it** - Uses built-in `pd.read_pickle()` → `from_df()`
✅ **Single conversion step** - Convert once, use forever
✅ **Minimal code changes** - Works with existing config
✅ **Fast loading** - Pickle is faster than NetCDF for tabular data

### Required DataFrame Schema

The pickle file must contain a pandas DataFrame with these columns:

| Column Name | Type | Description | Example |
|------------|------|-------------|---------|
| **pid** (or custom) | str | Proxy ID | 'Ocn-Bermuda.DraschbaA.2000' |
| **lat** (or custom) | float | Latitude | 32.3 |
| **lon** (or custom) | float | Longitude (0-360) | 295.5 |
| **elev** | float | Elevation (optional) | 0.0 |
| **time** (or 'year') | float/list | Years CE | [1920.0, 1917.0, ...] |
| **value** | float/list | Proxy measurements | [-3.22, -3.28, ...] |
| **ptype** | str | Proxy type | 'coral.d18O' |

**Important**: Each row can contain:
- **Scalar values** for metadata (pid, lat, lon, ptype)
- **Lists/arrays** for time-series data (time, value)

### DataFrame Structure Example

```python
import pandas as pd

df = pd.DataFrame({
    'pid': ['Ocn-Bermuda.DraschbaA.2000', 'Ocn-DryTortugas.DeLong.2014'],
    'lat': [32.3, 24.6],
    'lon': [295.5, 277.3],  # 0-360 range
    'elev': [0.0, 0.0],
    'time': [
        [1920.0, 1917.0, 1915.0],  # List of years for proxy 1
        [2000.0, 1995.0, 1990.0]   # List of years for proxy 2
    ],
    'value': [
        [-3.22, -3.28, -2.93],     # Measurements for proxy 1
        [-4.1, -4.2, -4.3]         # Measurements for proxy 2
    ],
    'ptype': ['coral.d18O', 'coral.d18O']
})

# Save as pickle
df.to_pickle('lipd_cfr.pkl')
```

---

## Implementation Plan

### Step 1: Create LiPD to DataFrame Converter

Create `convert_lipd_to_cfr_dataframe.py`:

```python
#!/usr/bin/env python3
"""
Convert LiPD pickle format to CFR-compatible pandas DataFrame pickle.

Usage:
    python convert_lipd_to_cfr_dataframe.py lipd.pkl lipd_cfr_dataframe.pkl
"""

import sys
import pickle
import pandas as pd
import numpy as np
from collections import OrderedDict


def extract_proxy_data(proxy_dict, proxy_id):
    """Extract data from a single LiPD proxy entry."""

    # Extract metadata
    lat = proxy_dict.get('geo', {}).get('geometry', {}).get('coordinates', [None, None])[1]
    lon = proxy_dict.get('geo', {}).get('geometry', {}).get('coordinates', [None, None])[0]

    # Normalize longitude to 0-360
    if lon is not None and lon < 0:
        lon = lon + 360

    # Extract archive type
    archive_type = proxy_dict.get('archiveType', '').lower()

    # Navigate to measurement data
    paleo_data = proxy_dict.get('paleoData', {})
    if isinstance(paleo_data, OrderedDict):
        paleo0 = paleo_data.get('paleo0', {})
        measurement_table = paleo0.get('measurementTable', {})

        if isinstance(measurement_table, OrderedDict):
            # Get first measurement table
            first_table_key = list(measurement_table.keys())[0]
            table = measurement_table[first_table_key]
            columns = table.get('columns', {})

            # Extract time and value arrays
            time_data = None
            value_data = None
            proxy_type = None

            for col_name, col_dict in columns.items():
                var_name = col_dict.get('variableName', '').lower()

                if var_name in ['year', 'age', 'time']:
                    time_data = col_dict.get('values', [])
                elif var_name in ['d18o', 'd18O', 'srca', 'trw', 'mxd']:
                    value_data = col_dict.get('values', [])
                    proxy_type = var_name

            # Construct ptype
            if proxy_type:
                ptype = f"{archive_type}.{proxy_type}"
            else:
                ptype = f"{archive_type}.unknown"

            return {
                'pid': proxy_id,
                'lat': lat,
                'lon': lon,
                'elev': 0.0,  # Default if not available
                'time': time_data if time_data else [],
                'value': value_data if value_data else [],
                'ptype': ptype
            }

    return None


def convert_lipd_to_dataframe(lipd_pkl_path):
    """Convert LiPD pickle to pandas DataFrame."""

    print(f"Loading LiPD pickle: {lipd_pkl_path}")
    with open(lipd_pkl_path, 'rb') as f:
        data = pickle.load(f)

    # Extract all proxies
    proxy_dict = data.get('D', {})
    print(f"Found {len(proxy_dict)} proxies in LiPD file")

    records = []
    skipped = 0

    for proxy_id, proxy_data in proxy_dict.items():
        record = extract_proxy_data(proxy_data, proxy_id)
        if record and len(record['time']) > 0 and len(record['value']) > 0:
            records.append(record)
        else:
            skipped += 1
            print(f"  Skipped {proxy_id}: missing time or value data")

    print(f"\nSuccessfully extracted {len(records)} proxies")
    print(f"Skipped {skipped} proxies (missing data)")

    # Create DataFrame
    df = pd.DataFrame(records)

    print(f"\nDataFrame shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nSample data:")
    print(df.head())

    return df


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    try:
        # Convert to DataFrame
        df = convert_lipd_to_dataframe(input_path)

        # Save as pickle
        print(f"\nSaving DataFrame pickle: {output_path}")
        df.to_pickle(output_path)

        # Verify
        print(f"\nVerifying saved file...")
        df_test = pd.read_pickle(output_path)
        print(f"✓ Successfully saved and verified!")
        print(f"✓ File ready for CFR loading")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Step 2: Run Conversion

```bash
python convert_lipd_to_cfr_dataframe.py lipd.pkl lipd_cfr.pkl
```

### Step 3: Update Configuration

Update `lmr_configs.yml`:

```yaml
proxydb_path: /app/lipd_cfr.pkl  # DataFrame pickle, not LiPD pickle
```

### Step 4: Update Workflow (if needed)

The workflow can stay mostly the same, but update the download step to get the DataFrame pickle:

```yaml
- name: Download lipd_cfr.pkl
  run: |
    python -m pip install --user gdown
    python -m gdown 'YOUR_DATAFRAME_PICKLE_URL' -O "${GITHUB_WORKSPACE}/lipd_cfr.pkl"
```

### Step 5: Load in CFR

CFR will automatically handle the DataFrame pickle:

```python
import cfr

# This will work automatically!
job = cfr.ReconJob()
job.load_proxydb('/app/lipd_cfr.pkl')  # Loads DataFrame pickle
```

CFR internally calls:
```python
df = pd.read_pickle('/app/lipd_cfr.pkl')
job.proxydb = ProxyDatabase().from_df(df)
```

---

## Alternative Solutions (Less Recommended)

### Alternative 1: Convert to NetCDF

**Pros**: Standard format, well-supported
**Cons**: More complex conversion, larger files, slower loading for tabular data

**Implementation**: Use the existing `convert_pickle_to_netcdf.py` but heavily modify to:
1. Create time grid for all proxies
2. Handle irregular sampling
3. Pad with NaN values

### Alternative 2: Convert to CSV

**Pros**: Human-readable, easy to debug
**Cons**: Larger file size, slower loading, awkward for variable-length time series

### Alternative 3: Modify CFR to Support LiPD

**Pros**: Direct support for LiPD format
**Cons**: Requires forking CFR, maintaining custom version, complex

---

## Expected Results

After conversion, you'll have:

1. **lipd_cfr.pkl** - DataFrame pickle (likely ~1-2 MB)
2. **Compatible with CFR** - Loads via existing `fetch()` method
3. **All 82 proxies** - Preserved from original LiPD file
4. **Fast loading** - Pickle is faster than NetCDF for DataFrames

### Usage in CFR

```python
import cfr

# In config file:
# proxydb_path: lipd_cfr.pkl

job = cfr.ReconJob()
job.run_da_cfg('lmr_configs.yml', run_mc=True)
# CFR automatically loads DataFrame pickle → from_df() → ProxyDatabase
```

---

## Testing Plan

### Test 1: Verify Conversion

```python
import pandas as pd

# Load converted pickle
df = pd.read_pickle('lipd_cfr.pkl')

# Check structure
print(f"Rows: {len(df)}")
print(f"Columns: {list(df.columns)}")
print(f"Proxy types: {df['ptype'].unique()}")
print(f"Sample row:\n{df.iloc[0]}")
```

### Test 2: Load with CFR

```python
import cfr

pdb = cfr.ProxyDatabase().fetch('lipd_cfr.pkl')
print(f"Loaded {pdb.nrec} proxy records")
print(f"Proxy IDs: {pdb.pids[:5]}")
```

### Test 3: Full CFR Workflow

```python
import cfr

job = cfr.ReconJob()
job.load_proxydb('lipd_cfr.pkl', verbose=True)
job.filter_proxydb(by='ptype', keys=['coral', 'tree'], verbose=True)
print(f"After filtering: {job.proxydb.nrec} proxies")
```

---

## Migration Guide

### For Workflow Migration

1. **Create converter script** (Step 1)
2. **Convert your LiPD pickle locally**:
   ```bash
   python convert_lipd_to_cfr_dataframe.py lipd.pkl lipd_cfr.pkl
   ```
3. **Upload DataFrame pickle** to your server or GitHub
4. **Update workflow** to download `lipd_cfr.pkl` instead of `lipd.pkl`
5. **Update config** to point to DataFrame pickle
6. **Test locally** before pushing to GitHub Actions

### For Local Development

```bash
# 1. Convert
python convert_lipd_to_cfr_dataframe.py lipd.pkl lipd_cfr.pkl

# 2. Test with CFR
python -c "
import cfr
pdb = cfr.ProxyDatabase().fetch('lipd_cfr.pkl')
print(f'Loaded {pdb.nrec} proxies')
"

# 3. Run full workflow
python cfr_main_code.py
```

---

## Troubleshooting

### Issue: "No module named 'cfr'"
**Solution**: Install CFR: `pip install cfr`

### Issue: "Column not found"
**Solution**: Specify custom column names in `from_df()`:
```python
pdb = cfr.ProxyDatabase().from_df(
    df,
    pid_column='pid',
    lat_column='lat',
    lon_column='lon',
    time_column='time',
    value_column='value',
    ptype_column='ptype'
)
```

### Issue: "Empty proxy records"
**Solution**: Check that time and value arrays are not empty in DataFrame

### Issue: "Longitude out of range"
**Solution**: Normalize longitude to 0-360 range during conversion

---

## Summary

**Recommended Approach**: LiPD Pickle → DataFrame Pickle

**Why**:
1. ✅ Simplest conversion (single script)
2. ✅ Native CFR support (no modifications needed)
3. ✅ Fast loading (pickle is optimized)
4. ✅ Minimal workflow changes (just swap files)

**Next Steps**:
1. Create converter script
2. Test conversion locally
3. Verify CFR can load the DataFrame
4. Update workflow and deploy

**Estimated Time**: 1-2 hours for implementation and testing

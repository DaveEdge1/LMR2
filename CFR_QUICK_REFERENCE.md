# CFR Proxy Data Loading - Quick Reference Guide

## Key Files in CFR Repository

| Component | File Path | Key Classes/Functions |
|-----------|-----------|---------------------|
| **Proxy Data Classes** | `cfr/proxy.py` | `ProxyRecord`, `ProxyDatabase` |
| **Reconstruction Job** | `cfr/reconjob.py` | `ReconJob` |
| **Utilities** | `cfr/utils.py` | `proxydb_url_dict`, download functions |

## Quick Loading Examples

### Load PAGES2kV2 from Cloud
```python
import cfr
pdb = cfr.ProxyDatabase().fetch('PAGES2kv2')
```

### Load NetCDF File (Local)
```python
pdb = cfr.ProxyDatabase().load_nc('/path/to/proxy_database.nc')
```

### Load CSV with Custom Columns
```python
import pandas as pd
df = pd.read_csv('proxies.csv')
pdb = cfr.ProxyDatabase().from_df(
    df,
    pid_column='ID',
    lat_column='latitude',
    lon_column='longitude',
    time_column='year',
    value_column='value',
    ptype_column='proxy_type'
)
```

### Complete ReconJob Workflow
```python
job = cfr.ReconJob()
job.load_proxydb('/path/to/proxy_database.nc')
job.filter_proxydb(by='ptype', keys=['tree', 'coral'])
job.annualize_proxydb(ptypes=['coral'], months=list(range(1,13)))
```

## Core Proxy Database Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `ProxyDatabase.fetch(name)` | proxy.py:1116 | Auto-detect and load any format |
| `ProxyDatabase.load_nc(path)` | proxy.py:1881 | Load NetCDF specifically |
| `ProxyDatabase.from_df(df, ...)` | proxy.py:1161 | Load from DataFrame |
| `ProxyDatabase.from_ds(ds)` | proxy.py:1848 | Load from xarray Dataset |
| `ProxyDatabase.filter(by, keys)` | proxy.py | Filter proxies |
| `ProxyDatabase.annualize(months)` | proxy.py | Annualize records |

## Supported File Formats

- **NetCDF (.nc)** - Direct support via `load_nc()`
- **JSON (.json)** - Via pandas
- **CSV (.csv)** - Via pandas
- **Pickle (.pkl)** - Via pandas
- **pandas.DataFrame** - Direct support via `from_df()`
- **xarray.Dataset** - Direct support via `from_ds()`

## Expected NetCDF Structure

```
File: proxy_database.nc

Variables (one per proxy site):
  ├── proxy_id_1 (time)
  │   └── Attributes: lat, lon, elev, ptype, dt, value_name, value_unit
  ├── proxy_id_2 (time)
  │   └── Attributes: (same as above)
  └── ... (more proxies)

Coordinates:
  └── time (shared across all variables)
```

## Proxy Type Format

Format: `archive.proxy`

Examples:
- `tree.TRW` - Tree-ring width
- `tree.MXD` - Maximum latewood density
- `coral.d18O` - Coral d18O isotopes
- `ice.d18O` - Ice core d18O
- `lake.varve_thickness` - Lake sediment varve thickness

## ReconJob Loading Pipeline

1. **Load Configuration**: YAML file with `proxydb_path`
2. **Load Proxy Database**: Via `job.load_proxydb(proxydb_path)`
3. **Filter Proxies**: Via `job.filter_proxydb(by='ptype', keys=[...])`
4. **Annualize Data**: Via `job.annualize_proxydb(ptypes=[...], months=[...])`
5. **Load Climate Data**: Via `job.load_clim(tag='prior'/'obs', path_dict={...})`
6. **Calibrate PSMs**: Via `job.calib_psms(...)`
7. **Run Reconstruction**: Via `job.run_da_cfg(cfg_path)`

## ProxyRecord Attributes

```python
ProxyRecord(
    pid='proxy_id',           # Unique identifier
    lat=45.5,                 # Latitude
    lon=120.5,                # Longitude
    elev=1500.0,              # Elevation (m)
    time=np.array([...]),     # Years CE
    value=np.array([...]),    # Proxy values
    ptype='tree.TRW',         # Proxy type
    value_name='TRW Index',   # Variable name
    value_unit='mm',          # Variable unit
    time_name='Year',         # Time axis name
    time_unit='yr CE'         # Time axis unit
)
```

## Configuration Example (lmr_configs.yml)

```yaml
proxydb_path: /app/PAGES2kV2.nc

filter_proxydb_kwargs:
  by: ptype
  keys:
  - coral
  - tree
  - ice
  - lake

annualize_proxydb_ptypes:
- coral

annualize_proxydb_months: 
- 1
- 2
- 3
- 4
- 5
- 6
- 7
- 8
- 9
- 10
- 11
- 12
```

## Custom Proxy Data Conversion

### Option 1: Convert Pickle to NetCDF
```bash
python convert_pickle_to_netcdf.py input.pkl output.nc
```

### Option 2: Convert CSV to NetCDF
```python
df = pd.read_csv('proxies.csv')
pdb = cfr.ProxyDatabase().from_df(df, pid_column='ID', ...)
pdb.to_nc('proxies.nc')
```

## Common Operations

### Access Individual Proxy
```python
record = pdb['proxy_id_string']
print(record.lat, record.lon, record.ptype)
print(record.time)    # years
print(record.value)   # proxy values
```

### Filter by Proxy Type
```python
tree_proxies = pdb.filter(by='ptype', keys=['tree.TRW', 'tree.MXD'])
```

### Get Statistics
```python
print(f"Number of records: {pdb.nrec}")
print(f"Proxy types: {pdb.type_dict}")
print(f"Proxy IDs: {pdb.pids}")
```

### Save and Load
```python
# Save to NetCDF
pdb.to_nc('my_proxies.nc')

# Load from NetCDF
pdb = cfr.ProxyDatabase().load_nc('my_proxies.nc')
```

## Troubleshooting

### Issue: Column names not found
**Solution**: Check your CSV headers and pass custom column name mappings
```python
pdb = cfr.ProxyDatabase().from_df(
    df,
    pid_column='your_id_column_name',
    lat_column='your_latitude_column_name',
    ...
)
```

### Issue: Proxy type not recognized
**Solution**: Use standard format `archive.proxy` or provide custom mapping

### Issue: Time data not loading properly
**Solution**: Ensure time axis is in years CE (numeric format)

---

## File Locations in This Analysis

1. **Complete Analysis**: `/home/user/LMR2/CFR_PROXY_DATA_LOADING_ANALYSIS.md`
2. **Quick Reference**: `/home/user/LMR2/CFR_QUICK_REFERENCE.md` (this file)
3. **Pickle to NetCDF Converter**: `/home/user/LMR2/convert_pickle_to_netcdf.py`
4. **Configuration Example**: `/home/user/LMR2/lmr_configs.yml`

---

## Key URLs

- **CFR Repository**: https://github.com/fzhu2e/cfr
- **CFR Documentation**: https://fzhu2e.github.io/cfr/
- **PAGES2kV2 Database**: https://github.com/fzhu2e/cfr-data/raw/main/pages2kv2.json
- **CFR Installation**: `pip install cfr`


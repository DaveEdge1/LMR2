# CFR Proxy Data Loading Analysis
## Complete Investigation of Climate Field Reconstruction Proxy Database Loading Pipeline

---

## 1. HOW CFR LOADS PROXY DATABASES

### Loading Pipeline Overview

The main entry point for loading proxy databases in CFR is through the `ReconJob` class, specifically the `load_proxydb()` method:

**File:** `/cfr/reconjob.py` (lines 130-149)

```python
def load_proxydb(self, path=None, verbose=False, **kwargs):
    ''' Load the proxy database from a `pandas.DataFrame`.
    
    Args:
        path (str, optional): the path to the pickle file of the `pandas.DataFrame`. Defaults to None.
        verbose (bool, optional): print verbose information. Defaults to False.
    '''
    path = self.io_cfg('proxydb_path', path, verbose=verbose)
    
    # self.proxydb = ProxyDatabase().from_df(df, **kwargs)
    self.proxydb = ProxyDatabase().fetch(name=path, **kwargs)
    if verbose:
        p_success(f'>>> {self.proxydb.nrec} records loaded')
        p_success(f'>>> job.proxydb created')
```

### The `ProxyDatabase.fetch()` Method

The primary method used for loading proxy data is `ProxyDatabase.fetch()` found in `/cfr/proxy.py` (lines 1116-1159):

```python
def fetch(self, name=None, **kwargs):
    ''' Fetch a proxy database from cloud
    
    Args:
        name (str): a predifined database name or an URL starting with "http" 
    '''
    url_dict = utils.proxydb_url_dict
    
    if name is None:
        p_warning(f'>>> Choose one from the supported databases:')
        for k in url_dict.keys():
            p_warning(f'- {k}')
        return None
    
    if name in url_dict:
        url = url_dict[name]
    else:
        url = name
    
    read_func = {
        '.json': pd.read_json,
        '.csv': pd.read_csv,
        '.pkl': pd.read_pickle,
    }
    ext = os.path.splitext(url)[-1].lower()
    if ext == '.nc':
        if url[:4] == 'http':
            # cloud
            fpath = '.cfr_download_tmp'
            if os.path.exists(fpath): os.remove(fpath)
            utils.download(url, fpath, show_bar=False)
            pdb = self.load_nc(fpath)
            os.remove(fpath)
        else:
            # local
            pdb = self.load_nc(url, **kwargs)
    elif ext in read_func:
        # cloud & local
        df = read_func[ext](url)
        pdb = self.from_df(df, **kwargs)
    else:
        raise ValueError('Wrong file extention based on the given URL!')
    
    return pdb
```

### The Loading Process Flow

1. **Configuration Phase**: `proxydb_path` is read from YAML configuration file
2. **Fetch Phase**: `ProxyDatabase().fetch(name=path)` is called
3. **Format Detection**: File extension determines loading method:
   - `.nc` → `load_nc()`
   - `.json` → pandas.read_json() → `from_df()`
   - `.csv` → pandas.read_csv() → `from_df()`
   - `.pkl` → pandas.read_pickle() → `from_df()`
4. **Database Construction**: ProxyDatabase object is populated with ProxyRecord objects

---

## 2. SUPPORTED FILE FORMATS FOR PROXY DATA

### Direct Format Support

| Format | Method | Location | Support |
|--------|--------|----------|---------|
| **NetCDF (.nc)** | `load_nc()` | proxy.py:1881 | ✓ Full support |
| **JSON (.json)** | Via pandas → `from_df()` | proxy.py:1116 | ✓ Full support |
| **CSV (.csv)** | Via pandas → `from_df()` | proxy.py:1116 | ✓ Full support |
| **Pickle (.pkl)** | Via pandas → `from_df()` | proxy.py:1116 | ✓ Full support |
| **pandas.DataFrame** | `from_df()` | proxy.py:1161 | ✓ Full support |
| **xarray.Dataset** | `from_ds()` | proxy.py:1848 | ✓ Full support |

### Format Conversion Pipeline

```
CSV/JSON/Pickle (tabular format)
    ↓
pandas.DataFrame
    ↓
ProxyDatabase.from_df()
    ↓
ProxyDatabase object

NetCDF file
    ↓
xarray.Dataset
    ↓
ProxyDatabase.load_nc() → ProxyDatabase.from_ds()
    ↓
ProxyDatabase object
```

---

## 3. EXPECTED DATA STRUCTURE AND SCHEMA FOR PROXY DATA

### ProxyRecord Schema

Each individual proxy record (one proxy site) has the following attributes:

**File:** `/cfr/proxy.py` (lines 133-184)

```python
class ProxyRecord:
    def __init__(self, 
        pid=None,              # Proxy ID (str) - unique identifier
        time=None,             # Time axis (numpy.array) - year CE
        value=None,            # Proxy values (numpy.array)
        lat=None,              # Latitude (float)
        lon=None,              # Longitude (float)
        elev=None,             # Elevation (float)
        ptype=None,            # Proxy type (str) - e.g., "tree.TRW"
        climate=None,          # Climate variable (str)
        tags=None,             # Tags for filtering (set of str)
        value_name=None,       # Name of the proxy variable
        value_unit=None,       # Unit of the proxy variable
        time_name=None,        # Name of time axis
        time_unit=None,        # Unit of time axis (default: 'yr')
        seasonality=None       # Seasonality information (list)
    ):
```

### ProxyDatabase Schema (xarray.Dataset)

When stored as NetCDF, the proxy database is an xarray.Dataset where:
- **Variables**: Each variable name is a proxy ID (pid)
- **Data**: Each variable contains proxy values with time coordinate
- **Attributes**: Each variable has attributes for metadata

**File:** `/cfr/proxy.py` (lines 1808-1846)

```python
# Expected Dataset structure when loaded from NetCDF:
# ds = xr.Dataset({
#     'proxy_id_1': xr.DataArray(values, dims=['time'], 
#         coords={'time': dates},
#         attrs={
#             'lat': float,
#             'lon': float,
#             'elev': float,
#             'ptype': str,      # e.g., 'tree.TRW'
#             'dt': float,       # temporal resolution
#             'time_name': str,
#             'time_unit': str,
#             'value_name': str,
#             'value_unit': str
#         }
#     ),
#     'proxy_id_2': ...
# })
```

### ProxyRecord.from_da() Method (xarray.DataArray Loading)

**File:** `/cfr/proxy.py` (lines 285-311)

```python
def from_da(self, da):
    ''' Get the time and value axis from the given xarray.DataArray
    
    Args:
        da (xarray.DataArray): the `xarray.DataArray` object to load from.
    '''
    new = ProxyRecord()
    # Time dimension handling
    if 'time' in da.dims:
        new.time = utils.datetime2year_float(da.time.values)
    elif 'year' in da.dims:
        new.time = da.year.values
    
    new.value = da.values
    new.time, new.value = utils.clean_ts(new.time, new.value)
    
    # Required attributes (all loaded from xarray attributes)
    new.pid = da.name
    new.lat = da.attrs['lat'] if 'lat' in da.attrs else None
    new.lon = da.attrs['lon'] if 'lon' in da.attrs else None
    new.elev = da.attrs['elev'] if 'elev' in da.attrs else None
    new.ptype = da.attrs['ptype'] if 'ptype' in da.attrs else None
    
    new.dt = np.median(np.diff(new.time))
    new.value_name = da.attrs['value_name'] if 'value_name' in da.attrs else None
    new.value_unit = da.attrs['value_unit'] if 'value_name' in da.attrs else None
    new.time_name = da.attrs['time_name'] if 'time_name' in da.attrs else None
    new.time_unit = da.attrs['time_unit'] if 'time_name' in da.attrs else None
    return new
```

### DataFrame Column Names (Default Schema)

**File:** `/cfr/proxy.py` (lines 1161-1164)

For loading from pandas DataFrame, the default column names are:

```python
pid_column='paleoData_pages2kID'      # Proxy ID
lat_column='geo_meanLat'              # Latitude
lon_column='geo_meanLon'              # Longitude
elev_column='geo_meanElev'            # Elevation
time_column='year'                    # Time in years
value_column='paleoData_values'       # Proxy values
proxy_type_column='paleoData_proxy'   # Proxy type (e.g., "TRW")
archive_type_column='archiveType'     # Archive type (e.g., "tree")
ptype_column='ptype'                  # Combined proxy type (e.g., "tree.TRW")
value_name_column='paleoData_variableName'  # Variable name
value_unit_column='paleoData_units'   # Variable unit
climate_column='climateInterpretation_variable'  # Climate variable
```

### Proxy Type (ptype) Values

Supported proxy types follow the format `archive.proxy`. Examples:

```
tree.TRW                    # Tree-ring width
tree.MXD                    # Maximum latewood density
coral.d18O                  # Coral d18O isotopes
coral.SrCa                  # Coral Sr/Ca ratios
ice.d18O                    # Ice core d18O
ice.dD                      # Deuterium measurements
lake.varve_thickness        # Lake sediment varve thickness
marine.MgCa                 # Marine sediment Mg/Ca
speleothem.d18O             # Speleothem d18O
```

---

## 4. EXAMPLES OF LOADING CUSTOM PROXY DATA

### Example 1: Loading from Remote NetCDF

```python
import cfr

# Load from predefined database
pdb = cfr.ProxyDatabase().fetch('PAGES2kv2')
```

### Example 2: Loading Local NetCDF File

**File:** `/cfr/proxy.py` (lines 1881-1890)

```python
import cfr

# Load from local NetCDF file
pdb = cfr.ProxyDatabase().load_nc('/path/to/proxy_database.nc')
```

### Example 3: Loading from pandas DataFrame with Custom Columns

**File:** `/cfr/proxy.py` (lines 1161-1181)

```python
import cfr
import pandas as pd

# Load from DataFrame with custom column names
df = pd.read_csv('my_proxy_data.csv')
pdb = cfr.ProxyDatabase().from_df(
    df, 
    pid_column='ID',
    lat_column='latitude',
    lon_column='longitude',
    elev_column='elevation',
    time_column='year',
    value_column='measurement',
    ptype_column='proxy_type',
    verbose=True
)
```

### Example 4: Loading from xarray.Dataset

**File:** `/cfr/proxy.py` (lines 1848-1860)

```python
import cfr
import xarray as xr

# Load from xarray Dataset
ds = xr.open_dataset('my_proxy_data.nc')
pdb = cfr.ProxyDatabase().from_ds(ds)
```

### Example 5: Complete Integration in ReconJob

**File:** `/cfr/reconjob.py` (lines 802-836)

```python
import cfr

# Initialize job
job = cfr.ReconJob()

# Load configuration
with open('lmr_configs.yml', 'r') as f:
    job.configs = yaml.safe_load(f)

# Load proxy database (from proxydb_path in config)
job.load_proxydb(job.configs['proxydb_path'], verbose=True)

# Optional: Filter the database
job.filter_proxydb(by='ptype', keys=['tree', 'coral'], verbose=True)

# Optional: Annualize specific proxy types
job.annualize_proxydb(
    months=job.configs['annualize_proxydb_months'],
    ptypes=job.configs['annualize_proxydb_ptypes']
)
```

---

## 5. NETCDF FILE LOADING FUNCTIONS

### Main NetCDF Loading Method

**File:** `/cfr/proxy.py` (lines 1881-1890)

```python
def load_nc(self, path, use_cftime=True, **kwargs):
    ''' Load the database from a netCDF file.
    
    Args:
        path (str): the path to save the file.
        use_cftime (bool): if True, use the cftime convention. Defaults to `True`.
    '''
    ds = xr.open_dataset(path, use_cftime=use_cftime, **kwargs)
    pdb = ProxyDatabase().from_ds(ds)
    return pdb
```

### Converting from xarray.Dataset

**File:** `/cfr/proxy.py` (lines 1848-1860)

```python
def from_ds(self, ds):
    ''' Load the proxy database from a `xarray.Dataset`
    
    Args:
        ds (xarray.Dataset): the xarray.Dataset to load from
    '''
    new = self.copy()
    for vn in ds.var():  # Iterates over all variable names
        da = ds[vn]      # Each variable is a ProxyRecord
        new.records[vn] = ProxyRecord().from_da(da)
    
    new.refresh()
    return new
```

### NetCDF File Structure Expected

```
File: proxy_database.nc

Variables:
  proxy_id_1 (time)     - float64 - Proxy values
    Attributes:
      lat               - float
      lon               - float
      elev              - float
      ptype             - string (e.g., "tree.TRW")
      dt                - float (temporal resolution)
      time_name         - string
      time_unit         - string
      value_name        - string
      value_unit        - string
  
  proxy_id_2 (time)     - float64 - Proxy values
    Attributes:
      ... (same as above)

Coordinates:
  time              - datetime64 or cftime (shared across variables)
```

### ProxyRecord.to_da() Method (For Creating NetCDF)

**File:** `/cfr/proxy.py` (lines 265-283)

```python
def to_da(self):
    ''' Convert to Xarray.DataArray for computation purposes
    '''
    dates = utils.year_float2datetime(self.time)
    da = xr.DataArray(
        self.value, dims=['time'], coords={'time': dates}, name=self.pid,
        attrs={
            'lat': self.lat,
            'lon': self.lon,
            'elev': np.nan if self.elev is None else self.elev,
            'ptype': self.ptype,
            'dt': self.dt,
            'time_name': 'time' if self.time_name is None else self.time_name,
            'time_unit': 'none' if self.time_unit is None else self.time_unit,
            'value_name': 'value' if self.value_name is None else self.value_name,
            'value_unit': 'none' if self.value_unit is None else self.value_unit,
        }
    )
    return da
```

### Loading Multiple NetCDF Files

**File:** `/cfr/proxy.py` (lines 1914-1940)

```python
def load_multi_nc(self, dirpath, nproc=None):
    ''' Load from multiple netCDF files (one per proxy).
    
    Args:
        dirpath (str): the directory path of the multiple .nc files
        nproc (int): the number of processors for loading
    '''
    paths = sorted(glob.glob(os.path.join(dirpath, '*.nc')))
    new = ProxyDatabase()
    
    if nproc is None: nproc = cpu_count()
    with Pool(nproc) as pool:
        das = list(
            tqdm(
                pool.imap(partial(xr.open_dataarray, use_cftime=True), paths),
                total=len(paths),
                desc='Loading .nc files',
            )
        )
    
    for da in das:
        pobj = ProxyRecord().from_da(da)
        new += pobj
    
    return new
```

---

## 6. RECONJOB CLASS DATA LOADING AND INITIALIZATION

### Main Data Preparation Pipeline

**File:** `/cfr/reconjob.py` (lines 802-880)

The `prep_da_cfg()` method is the primary initialization function:

```python
def prep_da_cfg(self, cfg_path, seeds=None, save_job=False, verbose=False):
    ''' Prepare the configuration items for data assimilation.
    
    Args:
        cfg_path (str): the path of the configuration YAML file.
        seeds (list, optional): the list of random seeds.
        save_job (bool, optional): if True, export the job object to a file.
        verbose (bool, optional): print verbose information. Defaults to False.
    '''
    # 1. Load configuration from YAML
    with open(cfg_path, 'r') as f:
        self.configs = yaml.safe_load(f)
    
    # 2. LOAD PROXY DATABASE
    self.load_proxydb(self.configs['proxydb_path'], verbose=verbose)
    
    # 3. FILTER PROXY DATABASE
    if 'pids' in self.configs:
        self.filter_proxydb(by='pid', keys=self.configs['pids'], verbose=verbose)
    if 'filter_proxydb_args' in self.configs and len(self.configs['filter_proxydb_args'])==2:
        args = self.configs['filter_proxydb_args']
        self.filter_proxydb(by=args[0], keys=args[1], verbose=verbose)
    if 'filter_proxydb_kwargs' in self.configs and len(self.configs['filter_proxydb_kwargs'])==2:
        kwargs = self.configs['filter_proxydb_kwargs']
        self.filter_proxydb(by=kwargs['by'], keys=kwargs['keys'], verbose=verbose)
    
    # 4. ANNUALIZE PROXY DATA
    self.annualize_proxydb(
        months=self.configs['annualize_proxydb_months'],
        ptypes=self.configs['annualize_proxydb_ptypes'])
    
    # 5. LOAD CLIMATE DATA (PRIOR and OBS)
    self.load_clim(tag='prior', path_dict=self.configs['prior_path'],
                   anom_period=self.configs[f'prior_anom_period'],
                   rename_dict=prior_rename_dict, verbose=verbose)
    self.load_clim(tag='obs', path_dict=self.configs['obs_path'],
                   anom_period=self.configs[f'obs_anom_period'],
                   rename_dict=obs_rename_dict, verbose=verbose)
    
    # 6. CALIBRATE PROXY SYSTEM MODELS (PSMs)
    self.calib_psms(ptype_psm_dict=self.configs['ptype_psm_dict'],
                    ptype_season_dict=self.configs['ptype_season_dict'],
                    ptype_clim_dict=self.configs['ptype_clim_dict'], verbose=verbose)
    
    # 7. FORWARD SIMULATE WITH PSMs
    self.forward_psms(verbose=verbose)
    
    # ... additional processing steps
```

### Configuration Example

**File:** `/home/user/LMR2/lmr_configs.yml` (relevant section)

```yaml
proxydb_path: /app/PAGES2kV2.nc   # NetCDF file location

# Proxy filtering configuration
filter_proxydb_kwargs:
  by: ptype
  keys:
  - coral
  - tree
  - ice
  - lake
  - bivalve

# Proxy annualization configuration
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

### Proxy System Model (PSM) Calibration

**File:** `/cfr/reconjob.py` (lines 390-478)

```python
def calib_psms(self, ptype_psm_dict=None, ptype_season_dict=None, ptype_clim_dict=None, verbose=False):
    ''' Calibrate the Proxy System Models (PSMs).
    
    This step fits forward models for each proxy record, creating proxyRecord.psm objects.
    The PSMs define how climate variables predict proxy values.
    '''
    # For each proxy record in the database:
    for pid, pobj in tqdm(self.proxydb.records.items(), total=self.proxydb.nrec, 
                          desc='Calibrating the PSMs'):
        # Calibrate PSM for this proxy
        # ... (PSM calibration logic)
        self.proxydb.records[pid].tags.add('calibrated')
        self.proxydb.records[pid].R = pobj.psm.calib_details['PSMmse']
```

---

## 7. CUSTOM PROXY DATA CONVERSION (Pickle to NetCDF)

### Local Solution: Converting Pickle to NetCDF

**File:** `/home/user/LMR2/convert_pickle_to_netcdf.py`

The repository includes a conversion utility for custom proxy data:

```python
def convert_proxy_database(data):
    """
    Convert a proxy database dictionary to xarray Dataset.
    Assumes data has structure like: {key: [values...]} where values are per-proxy.
    """
    # Determine the number of proxies
    n_proxies = None
    for key, value in data.items():
        if isinstance(value, (list, np.ndarray)):
            n_proxies = len(value)
            break
    
    # Create coordinate
    proxy_dim = np.arange(n_proxies)
    
    # Convert each key to a DataArray
    data_vars = {}
    coords = {}
    
    for key, value in data.items():
        if isinstance(value, (list, np.ndarray)):
            if isinstance(value, list):
                if value and isinstance(value[0], str):
                    arr = np.array(value, dtype=object)
                else:
                    arr = np.array(value)
            else:
                arr = value
            
            # Create DataArray
            if len(arr.shape) == 1 and len(arr) == n_proxies:
                data_vars[key] = xr.DataArray(arr, dims=['proxy'])
            elif len(arr.shape) == 2:
                # 2D array, add time dimension
                data_vars[key] = xr.DataArray(arr, dims=['proxy', 'time'])
    
    # Create the Dataset
    ds = xr.Dataset(data_vars, coords={'proxy': proxy_dim})
    return ds
```

---

## 8. KEY ATTRIBUTES AND METHODS SUMMARY

### ProxyDatabase Class Key Methods

| Method | Location | Purpose |
|--------|----------|---------|
| `fetch(name)` | proxy.py:1116 | Load from cloud or local file (auto-detects format) |
| `load_nc(path)` | proxy.py:1881 | Load from NetCDF file |
| `from_df(df, ...)` | proxy.py:1161 | Create from pandas DataFrame |
| `from_ds(ds)` | proxy.py:1848 | Create from xarray Dataset |
| `to_nc(path)` | proxy.py:1862 | Save to NetCDF file |
| `to_ds(...)` | proxy.py:1808 | Convert to xarray Dataset |
| `to_df()` | (in filter/slice) | Convert to DataFrame |
| `filter(by, keys)` | proxy.py | Filter by proxy type, ID, tags, etc. |
| `annualize(months)` | proxy.py | Annualize proxy records |
| `slice(timespan)` | proxy.py | Extract time period |
| `center(ref_period)` | proxy.py | Center records to baseline |
| `standardize(ref_period)` | proxy.py | Standardize records |

### ProxyRecord Class Key Methods

| Method | Location | Purpose |
|--------|----------|---------|
| `load_nc(path)` | proxy.py:255 | Load from NetCDF file |
| `from_da(da)` | proxy.py:285 | Create from xarray DataArray |
| `to_nc(path)` | proxy.py:237 | Save to NetCDF file |
| `to_da()` | proxy.py:265 | Convert to xarray DataArray |
| `annualize(months)` | proxy.py:313 | Annualize the record |
| `slice(timespan)` | proxy.py:190 | Extract time period |
| `center(ref_period)` | proxy.py:336 | Center to baseline |
| `standardize(ref_period)` | proxy.py:381 | Standardize the record |

### ReconJob Class Key Proxy-Related Methods

| Method | Location | Purpose |
|--------|----------|---------|
| `load_proxydb(path)` | reconjob.py:130 | Load proxy database from config path |
| `filter_proxydb(*args)` | reconjob.py:151 | Filter loaded proxy database |
| `annualize_proxydb(...)` | reconjob.py:195 | Annualize proxy types |
| `slice_proxydb(timespan)` | reconjob.py:176 | Slice to time period |
| `center_proxydb(ref_period)` | reconjob.py:228 | Center to baseline |
| `calib_psms(...)` | reconjob.py:390 | Calibrate proxy system models |
| `prep_da_cfg(cfg_path)` | reconjob.py:802 | Full preparation pipeline |
| `run_da_cfg(cfg_path)` | reconjob.py:1151 | Run complete reconstruction |

---

## 9. SUPPORTED PROXY DATABASES (Predefined)

From `/cfr/utils.py` (lines 656-680+):

```python
proxydb_url_dict = {
    'PAGES2kv2': 'https://github.com/fzhu2e/cfr-data/raw/main/pages2kv2.json',
    'pseudoPAGES2k/ppwn_SNRinf_rta': 'https://github.com/fzhu2e/paper-pseudoPAGES2k/raw/main/data/ppwn_SNRinf_rta.nc',
    'pseudoPAGES2k/ppwn_SNR10_rta': '...',
    'pseudoPAGES2k/ppwn_SNR2_rta': '...',
    'pseudoPAGES2k/ppwn_SNR1_rta': '...',
    'pseudoPAGES2k/ppwn_SNR0.5_rta': '...',
    'pseudoPAGES2k/ppwn_SNR0.25_rta': '...',
    'pseudoPAGES2k/ppwn_SNRinf_fta': '...',
    'pseudoPAGES2k/ppwn_SNR10_fta': '...',
    'pseudoPAGES2k/ppwn_SNR2_fta': '...',
    # ... and more
}
```

---

## 10. COMPLETE WORKING EXAMPLE

### Full Workflow Example

```python
import cfr
import yaml

# Step 1: Load configuration
with open('lmr_configs.yml', 'r') as f:
    config = yaml.safe_load(f)

# Step 2: Create ReconJob
job = cfr.ReconJob(config, verbose=True)

# Step 3: Load proxy database
# This reads proxydb_path from config, auto-detects format
job.load_proxydb(config['proxydb_path'], verbose=True)
# Output: ">>> 692 records loaded"

# Step 4: Filter proxies (optional)
job.filter_proxydb(
    by='ptype',
    keys=['coral', 'tree', 'ice', 'lake'],
    verbose=True
)
# Output: ">>> X records remaining"

# Step 5: Annualize specific proxies (optional)
job.annualize_proxydb(
    ptypes=['coral'],
    months=list(range(1, 13)),
    verbose=True
)

# Step 6: Load climate data
job.load_clim(
    tag='prior',
    path_dict=config['prior_path'],
    anom_period=config['prior_anom_period'],
    verbose=True
)

# Step 7: Calibrate PSMs
job.calib_psms(
    ptype_psm_dict=config['ptype_psm_dict'],
    ptype_season_dict=config['ptype_season_dict'],
    ptype_clim_dict=config['ptype_clim_dict'],
    verbose=True
)

# Access the loaded data
print(f"Number of proxy records: {job.proxydb.nrec}")
print(f"Proxy IDs: {job.proxydb.pids[:10]}")
print(f"Proxy types: {job.proxydb.type_dict}")

# Access individual record
record = job.proxydb['NAm_153']
print(f"Record time span: {record.time.min()}-{record.time.max()}")
print(f"Record location: ({record.lat}, {record.lon})")
print(f"Record type: {record.ptype}")
```

---

## Summary

CFR uses a flexible proxy data loading system that:

1. **Supports multiple formats**: NetCDF, JSON, CSV, Pickle, pandas DataFrame, xarray Dataset
2. **Auto-detects format**: Based on file extension
3. **Handles both cloud and local data**: Can fetch from GitHub or local files
4. **Provides flexible schema mapping**: Column names can be customized for from_df()
5. **Stores as xarray**: Internally uses xarray for efficient handling
6. **Implements filtering and processing**: Supports filtering, annualizing, centering, standardizing
7. **Integrates with PSMs**: Each proxy is associated with a Proxy System Model
8. **Part of larger workflow**: ProxyDatabase loading is one step in the full data assimilation pipeline

The key entry point is `ProxyDatabase.fetch()` which intelligently routes to the appropriate loading method based on file format and location (cloud vs. local).


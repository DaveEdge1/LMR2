# CFR Proxy Data Loading - Key Files and Functions Reference

## Source Files Downloaded and Analyzed

### 1. cfr/proxy.py
**Location**: https://raw.githubusercontent.com/fzhu2e/cfr/master/cfr/proxy.py  
**Size**: 80 KB  
**Key Classes**:
- `ProxyRecord` (line 129) - Individual proxy record
- `ProxyDatabase` (line 1027) - Collection of proxy records

**Key Functions**:
- `get_ptype()` (line 35) - Convert archive/proxy types to standard format
- `ProxyRecord.from_da()` (line 285) - Load from xarray.DataArray
- `ProxyRecord.to_da()` (line 265) - Convert to xarray.DataArray
- `ProxyRecord.load_nc()` (line 255) - Load from NetCDF file
- `ProxyDatabase.fetch()` (line 1116) - Main loading function (auto-detects format)
- `ProxyDatabase.from_df()` (line 1161) - Load from pandas DataFrame
- `ProxyDatabase.from_ds()` (line 1848) - Load from xarray Dataset
- `ProxyDatabase.load_nc()` (line 1881) - Load from NetCDF file
- `ProxyDatabase.load_multi_nc()` (line 1914) - Load from multiple NetCDF files
- `ProxyDatabase.to_nc()` (line 1862) - Save to NetCDF file
- `ProxyDatabase.to_ds()` (line 1808) - Convert to xarray Dataset

### 2. cfr/reconjob.py
**Location**: https://raw.githubusercontent.com/fzhu2e/cfr/master/cfr/reconjob.py  
**Size**: 60 KB  
**Key Classes**:
- `ReconJob` (line 40) - Main reconstruction job class

**Key Methods**:
- `load_proxydb()` (line 130) - Load proxy database from config path
- `filter_proxydb()` (line 151) - Filter loaded proxy database
- `annualize_proxydb()` (line 195) - Annualize proxy records
- `slice_proxydb()` (line 176) - Slice proxy database to time period
- `center_proxydb()` (line 228) - Center proxy records
- `calib_psms()` (line 390) - Calibrate proxy system models
- `prep_da_cfg()` (line 802) - Main preparation pipeline
- `run_da_cfg()` (line 1151) - Run complete data assimilation

### 3. cfr/utils.py
**Location**: https://raw.githubusercontent.com/fzhu2e/cfr/master/cfr/utils.py  
**Size**: Large utility file  
**Key Variables**:
- `proxydb_url_dict` (line 656) - Predefined database URLs

### 4. cfr/__init__.py
**Location**: https://raw.githubusercontent.com/fzhu2e/cfr/master/cfr/__init__.py  
**Size**: 750 bytes  
**Exports**: Main classes and functions

## Local Files (LMR2 Repository)

### 1. lmr_configs.yml
**Location**: `/home/user/LMR2/lmr_configs.yml`  
**Purpose**: Configuration file for reconstruction  
**Key Settings**:
- `proxydb_path: /app/PAGES2kV2.nc` (line 75)
- `filter_proxydb_kwargs` (lines 60-70) - Proxy filtering
- `annualize_proxydb_ptypes` (lines 179-182) - Annualization types
- `ptype_psm_dict` (lines 138-146) - PSM assignment by proxy type

### 2. convert_pickle_to_netcdf.py
**Location**: `/home/user/LMR2/convert_pickle_to_netcdf.py`  
**Purpose**: Utility to convert pickle files to NetCDF format  
**Key Functions**:
- `examine_pickle_structure()` - Examine pickle file structure
- `convert_to_netcdf()` - Main conversion function
- `convert_proxy_database()` - Custom proxy database conversion

### 3. PICKLE_TO_NETCDF_README.md
**Location**: `/home/user/LMR2/PICKLE_TO_NETCDF_README.md`  
**Purpose**: Documentation for pickle to NetCDF conversion

---

## Function Call Flow for Proxy Loading

### Path 1: Direct ProxyDatabase.fetch()
```
ProxyDatabase().fetch(path)
  ├─ Check file extension
  ├─ If .nc:
  │  └─ ProxyDatabase().load_nc(path)
  │     └─ xr.open_dataset(path)
  │        └─ ProxyDatabase().from_ds(ds)
  │           └─ ProxyRecord().from_da(da) [for each variable]
  │
  ├─ If .json/.csv/.pkl:
  │  ├─ pandas.read_* (appropriate function)
  │  └─ ProxyDatabase().from_df(df, column_mappings)
  │     └─ ProxyRecord() [for each row]
  │
  └─ Return ProxyDatabase object
```

### Path 2: ReconJob.load_proxydb()
```
ReconJob().load_proxydb(path)
  └─ ProxyDatabase().fetch(path)
     └─ [Same as Path 1 above]
     └─ Stores in self.proxydb
```

### Path 3: Complete Workflow (ReconJob.prep_da_cfg)
```
ReconJob().prep_da_cfg(cfg_path)
  1. Load YAML config
  2. ReconJob().load_proxydb(config['proxydb_path'])
     └─ ProxyDatabase().fetch()
  3. ReconJob().filter_proxydb(by='ptype', keys=[...])
  4. ReconJob().annualize_proxydb(ptypes=[...], months=[...])
  5. ReconJob().load_clim(tag='prior')
  6. ReconJob().load_clim(tag='obs')
  7. ReconJob().calib_psms(ptype_psm_dict, ...)
  8. ReconJob().forward_psms()
```

---

## Data Structure Summary

### ProxyRecord Instance
```
ProxyRecord(
    pid: str                      # Unique proxy ID
    lat: float                    # Latitude (-90 to 90)
    lon: float                    # Longitude (0 to 360)
    elev: float                   # Elevation in meters
    time: numpy.array[float]      # Years CE
    value: numpy.array[float]     # Proxy values
    ptype: str                    # Format: "archive.proxy"
    climate: str                  # Climate variable
    tags: set[str]                # Tags for filtering
    value_name: str               # Variable name
    value_unit: str               # Variable units
    time_name: str                # Time axis name
    time_unit: str                # Time axis units (default: 'yr')
    seasonality: list             # Seasonality info [1-12]
    dt: float                     # Temporal resolution
    psm: PSM object               # Proxy System Model (after calib)
    R: float                      # Observation error variance (after calib)
)
```

### ProxyDatabase Instance
```
ProxyDatabase(
    records: OrderedDict[str, ProxyRecord]   # All proxies
    source: str                              # Source file path
    
    Properties:
    nrec: int                    # Number of records
    pids: list[str]              # All proxy IDs
    lats: list[float]            # All latitudes
    lons: list[float]            # All longitudes
    elevs: list[float]           # All elevations
    type_list: list[str]         # All proxy types
    type_dict: dict[str, int]    # Proxy type counts
)
```

### xarray.Dataset Structure (for NetCDF)
```
xr.Dataset({
    'proxy_id_1': xr.DataArray(
        data=values,             # 1D float array
        dims=['time'],
        coords={'time': dates},  # datetime64 or cftime
        name='proxy_id_1',
        attrs={
            'lat': float,
            'lon': float,
            'elev': float,
            'ptype': str,
            'dt': float,
            'time_name': str,
            'time_unit': str,
            'value_name': str,
            'value_unit': str
        }
    ),
    'proxy_id_2': xr.DataArray(...),
    ...
})
```

---

## Supported Proxy Types (ptype)

### Trees
- `tree.TRW` - Tree-ring width
- `tree.MXD` - Maximum latewood density
- `tree.ENSO` - Tree-based ENSO

### Corals
- `coral.d18O` - Coral d18O isotopes
- `coral.SrCa` - Coral Sr/Ca ratios
- `coral.d18Osw` - Coral d18O seawater
- `coral.calc` - Coral calcification

### Ice
- `ice.d18O` - Ice core d18O
- `ice.dD` - Deuterium measurements
- `ice.melt` - Melt fraction
- `ice.d-excess` - Deuterium excess

### Lake Sediments
- `lake.varve_thickness` - Varve thickness
- `lake.varve_property` - Varve properties
- `lake.accumulation` - Sediment accumulation
- `lake.chironomid` - Chironomid assemblages
- `lake.diatom` - Diatom assemblages
- `lake.TEX86` - TEX86 index
- `lake.d18O` - Lake d18O

### Marine Sediments
- `marine.d18O` - Foram d18O
- `marine.MgCa` - Foram Mg/Ca
- `marine.TEX86` - TEX86 index
- `marine.UK37` - Alkenone UK'37
- `marine.foram` - Foraminiferal assemblages
- `marine.diatom` - Diatom assemblages

### Other
- `speleothem.d18O` - Speleothem d18O
- `bivalve.d18O` - Bivalve d18O

---

## Configuration File Keys (lmr_configs.yml)

### Proxy Database Settings
```yaml
proxydb_path: str              # Path to proxy database file (required)

filter_proxydb_kwargs:
  by: str                      # Filter attribute ('ptype', 'pid', etc.)
  keys: list[str]              # Filter values

annualize_proxydb_ptypes:
  - str                        # Proxy types to annualize

annualize_proxydb_months:
  - int                        # Months for annualization (1-12)

nobs_lb: int                   # Minimum observations per proxy
```

### Proxy System Model Settings
```yaml
ptype_psm_dict:               # PSM type for each proxy type
  archive.proxy: "Linear"     # "Linear" or "Bilinear"

ptype_season_dict:            # Seasonality for each proxy type
  archive.proxy: [int, ...]   # Months (1-12) for seasonality

ptype_clim_dict:              # Climate variables for each proxy
  archive.proxy: [str, ...]   # ['tas'] or ['tas', 'pr']
```

---

## NetCDF File Creation/Loading

### Create NetCDF from ProxyDatabase
```python
pdb = cfr.ProxyDatabase()
# ... populate pdb with records ...
pdb.to_nc('output.nc')
```

### Load NetCDF back to ProxyDatabase
```python
pdb = cfr.ProxyDatabase().load_nc('output.nc')
```

### Expected NetCDF Variables
Each variable in the NetCDF file represents one proxy record:
- Variable name = Proxy ID
- Variable data = proxy values (1D array)
- Dimension = 'time'
- Attributes = metadata (lat, lon, elev, ptype, etc.)
- Shared coordinate = 'time' (datetime values)

---

## Important Implementation Details

1. **Longitude Normalization**: Longitude values are normalized to 0-360 range
   ```python
   lon = np.mod(lon, 360)  # In ProxyRecord.__init__
   ```

2. **Time Format**: 
   - Internal storage: float years CE (e.g., 1500.5)
   - NetCDF storage: datetime64 or cftime objects
   - Conversion: `utils.datetime2year_float()` and `utils.year_float2datetime()`

3. **Temporal Resolution**: 
   - Calculated as median of time differences
   - Used for sampling in data assimilation

4. **Missing Data Handling**:
   - Function `utils.clean_ts()` removes NaN values
   - Ensures time and value arrays have same length

5. **PSM Calibration**:
   - Each ProxyRecord gets a `.psm` object after calibration
   - Stores model details and observation error variance `.R`
   - Tagged with 'calibrated' in `.tags`

---

## Testing and Examples

### Simple Test: Load and Inspect
```python
import cfr

# Load PAGES2kV2
pdb = cfr.ProxyDatabase().fetch('PAGES2kv2')

# Access properties
print(pdb.nrec)           # 692 records
print(pdb.type_dict)      # {'tree.TRW': 345, 'coral.d18O': 120, ...}

# Access specific record
rec = pdb['NAm_153']
print(rec.lat, rec.lon, rec.ptype)
print(len(rec.time), len(rec.value))
```

### Create Custom Database
```python
import cfr
import numpy as np

pdb = cfr.ProxyDatabase()

# Create a record
rec = cfr.ProxyRecord(
    pid='test_001',
    lat=45.0,
    lon=120.0,
    elev=1500.0,
    time=np.arange(1000, 2001),
    value=np.random.randn(1001),
    ptype='tree.TRW',
    value_name='TRW Index',
    value_unit='mm'
)

pdb.records['test_001'] = rec
pdb.refresh()

# Save
pdb.to_nc('test.nc')

# Load back
pdb2 = cfr.ProxyDatabase().load_nc('test.nc')
```


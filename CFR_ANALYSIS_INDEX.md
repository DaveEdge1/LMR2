# CFR Proxy Data Loading Analysis - Complete Documentation Index

Generated: December 16, 2024  
Thoroughness Level: Very Thorough  
Source: https://github.com/fzhu2e/cfr

---

## Documentation Files Created

This analysis contains 4 comprehensive documents detailing how CFR loads proxy data:

### 1. **CFR_PROXY_DATA_LOADING_ANALYSIS.md** (24 KB)
**Comprehensive Technical Analysis**

The main detailed analysis covering all aspects of proxy data loading in CFR.

**Sections:**
- How CFR loads proxy databases (complete pipeline)
- Supported file formats (NetCDF, JSON, CSV, Pickle, DataFrame, xarray)
- Expected data structure and schema for proxy databases
- ProxyRecord and ProxyDatabase class structure
- Default column name mappings for DataFrames
- Examples of loading custom proxy data
- NetCDF file loading functions and structure
- ReconJob class data loading and initialization
- Complete working examples

**Key Findings:**
- ProxyDatabase.fetch() is the main entry point (auto-detects format)
- CFR supports 6+ input formats with automatic detection
- NetCDF is the primary storage format internally
- Each proxy is a ProxyRecord with time/value arrays + metadata
- Complete data pipeline: Config → Load → Filter → Annualize → Calibrate → Reconstruct

### 2. **CFR_QUICK_REFERENCE.md** (5.9 KB)
**Quick Lookup Guide for Common Tasks**

Concise reference guide for quick lookup while working with CFR.

**Contents:**
- Key file locations in CFR
- Quick loading examples (cloud and local)
- Core proxy database functions
- Supported file formats summary
- Expected NetCDF structure diagram
- Proxy type format reference
- ReconJob loading pipeline steps
- ProxyRecord attributes
- Configuration YAML example
- Custom data conversion examples
- Common operations and troubleshooting

**Best For:** Quick reference while coding, remembering syntax, command examples

### 3. **CFR_FILES_AND_FUNCTIONS.md** (11 KB)
**Complete Function Reference and Implementation Details**

Detailed reference of all source files, functions, and data structures.

**Includes:**
- Source files downloaded and analyzed
  - cfr/proxy.py (key classes and functions)
  - cfr/reconjob.py (ReconJob methods)
  - cfr/utils.py (utilities and URL dictionary)
  - cfr/__init__.py (exports)
- Local files in LMR2 repository
- Function call flow diagrams (3 loading paths)
- Complete ProxyRecord data structure
- Complete ProxyDatabase data structure
- xarray.Dataset structure for NetCDF
- All supported proxy types (tree, coral, ice, lake, marine, etc.)
- Configuration file keys with examples
- Important implementation details
- Testing and example code

**Best For:** Understanding implementation details, creating custom code, debugging

### 4. **CFR_ANALYSIS_INDEX.md** (this file)
**Navigation Guide and Overview**

This file serves as the index and navigation guide for all analysis documents.

---

## Quick Navigation Guide

### I want to... | Read this section

| Task | Document | Section |
|------|----------|---------|
| **Understand the overall architecture** | CFR_PROXY_DATA_LOADING_ANALYSIS.md | Section 1: How CFR Loads Proxy Databases |
| **Load a proxy database quickly** | CFR_QUICK_REFERENCE.md | Quick Loading Examples |
| **See file formats supported** | CFR_PROXY_DATA_LOADING_ANALYSIS.md | Section 2: Supported File Formats |
| **Understand data structure** | CFR_PROXY_DATA_LOADING_ANALYSIS.md | Section 3: Expected Data Structure |
| **Load custom data** | CFR_PROXY_DATA_LOADING_ANALYSIS.md | Section 4: Loading Custom Proxy Data |
| **Learn about NetCDF files** | CFR_PROXY_DATA_LOADING_ANALYSIS.md | Section 5: NetCDF File Loading |
| **Understand ReconJob** | CFR_PROXY_DATA_LOADING_ANALYSIS.md | Section 6: ReconJob Class |
| **Convert pickle to NetCDF** | CFR_QUICK_REFERENCE.md | Custom Proxy Data Conversion |
| **Find a specific function** | CFR_FILES_AND_FUNCTIONS.md | Source Files section |
| **See function call flow** | CFR_FILES_AND_FUNCTIONS.md | Function Call Flow section |
| **Understand ProxyRecord** | CFR_FILES_AND_FUNCTIONS.md | Data Structure Summary |
| **See all proxy types** | CFR_FILES_AND_FUNCTIONS.md | Supported Proxy Types |
| **Configure YAML file** | CFR_FILES_AND_FUNCTIONS.md | Configuration File Keys |
| **Create test code** | CFR_FILES_AND_FUNCTIONS.md | Testing and Examples |

---

## Key Findings Summary

### 1. Main Entry Point
- **Function**: `ProxyDatabase.fetch(name_or_path)`
- **Location**: `/cfr/proxy.py` line 1116
- **Intelligence**: Auto-detects file format based on extension
- **Supports**: .nc, .json, .csv, .pkl, pandas.DataFrame, xarray.Dataset

### 2. File Format Support

| Format | Method | Route |
|--------|--------|-------|
| NetCDF (.nc) | `load_nc()` | Direct via xarray |
| JSON/CSV/Pickle | `fetch()` | pandas.read_* → from_df() |
| pandas.DataFrame | `from_df()` | Direct construction |
| xarray.Dataset | `from_ds()` | Direct construction |

### 3. Core Data Classes

**ProxyRecord** - Individual proxy site data
- Attributes: pid, lat, lon, elev, time, value, ptype, climate, tags, etc.
- Methods: load_nc(), from_da(), to_da(), annualize(), center(), etc.

**ProxyDatabase** - Collection of proxy records
- Attributes: records (dict), source
- Properties: nrec, pids, lats, lons, elevs, type_list, type_dict
- Methods: fetch(), load_nc(), from_df(), from_ds(), filter(), annualize(), etc.

### 4. ReconJob Pipeline

```
prep_da_cfg() {
  1. Load YAML config
  2. Load proxy database (fetch)
  3. Filter proxies (by ptype/pid/etc.)
  4. Annualize specific types
  5. Load climate data (prior & obs)
  6. Calibrate Proxy System Models (PSMs)
  7. Forward simulate with PSMs
}
```

### 5. NetCDF Schema
- Each variable = one proxy record (name = proxy ID)
- Each variable has 'time' dimension
- Attributes stored: lat, lon, elev, ptype, dt, value_name, value_unit, etc.
- Shared coordinate: 'time' (datetime64 or cftime)

### 6. Configuration Essentials
```yaml
proxydb_path: /path/to/database.nc
filter_proxydb_kwargs:
  by: ptype
  keys: [coral, tree, ice, lake]
annualize_proxydb_ptypes: [coral]
ptype_psm_dict: {tree.TRW: Bilinear, coral.d18O: Linear}
```

### 7. Proxy Types Supported
30+ proxy types organized by archive:
- **Trees**: TRW, MXD, ENSO
- **Corals**: d18O, SrCa, d18Osw, calc
- **Ice**: d18O, dD, melt, d-excess, 15N40Ar
- **Lake**: varve_thickness, varve_property, accumulation, chironomid, diatom, TEX86
- **Marine**: d18O, MgCa, TEX86, UK37, foram, diatom
- **Other**: speleothem.d18O, bivalve.d18O

---

## Code Examples from Analysis

### Example 1: Load Cloud Database
```python
import cfr
pdb = cfr.ProxyDatabase().fetch('PAGES2kv2')
print(f"Loaded {pdb.nrec} proxy records")
```

### Example 2: Load Local NetCDF
```python
pdb = cfr.ProxyDatabase().load_nc('/path/to/proxies.nc')
```

### Example 3: Load CSV with Custom Columns
```python
import pandas as pd
df = pd.read_csv('proxies.csv')
pdb = cfr.ProxyDatabase().from_df(
    df,
    pid_column='ID',
    lat_column='latitude',
    time_column='year',
    ptype_column='proxy_type'
)
```

### Example 4: Complete ReconJob Workflow
```python
job = cfr.ReconJob()
job.prep_da_cfg('lmr_configs.yml')
job.run_da_cfg('lmr_configs.yml', run_mc=True)
```

---

## Source Files Analyzed

### From CFR Repository (https://github.com/fzhu2e/cfr)
1. **cfr/proxy.py** (80 KB)
   - ProxyRecord class (line 129)
   - ProxyDatabase class (line 1027)
   - Core loading functions

2. **cfr/reconjob.py** (60 KB)
   - ReconJob class (line 40)
   - Data loading pipeline
   - PSM calibration

3. **cfr/utils.py**
   - proxydb_url_dict (line 656)
   - Helper functions

4. **cfr/__init__.py**
   - Package exports

### From LMR2 Repository (Local)
1. **lmr_configs.yml**
   - Example configuration with PAGES2kV2.nc

2. **convert_pickle_to_netcdf.py**
   - Utility for custom data conversion

3. **PICKLE_TO_NETCDF_README.md**
   - Documentation for conversion

---

## Data Types and Formats

### Time Format
- **Internal**: float (years CE, e.g., 1500.5)
- **NetCDF**: datetime64 or cftime objects
- **Conversion**: utils.datetime2year_float() ↔ utils.year_float2datetime()

### Longitude
- **Normalized**: 0-360 range
- **Operation**: `np.mod(lon, 360)`

### Proxy Types
- **Format**: `archive.proxy` (e.g., "tree.TRW")
- **Parser**: get_ptype(archive_type, proxy_type) function

### DataFrame Columns (PAGES2k Schema)
- pid_column: 'paleoData_pages2kID'
- lat_column: 'geo_meanLat'
- lon_column: 'geo_meanLon'
- time_column: 'year'
- value_column: 'paleoData_values'
- ptype_column: 'ptype'

---

## Related Tools and Utilities

### Within Analysis Package
- **convert_pickle_to_netcdf.py**: Convert custom pickle files to NetCDF
- **CFR_QUICK_REFERENCE.md**: For quick lookups while coding

### External Resources
- **CFR Official Docs**: https://fzhu2e.github.io/cfr/
- **CFR GitHub**: https://github.com/fzhu2e/cfr
- **PAGES2kV2 Database**: JSON at https://github.com/fzhu2e/cfr-data/

---

## Document Statistics

| Document | Size | Content | Sections |
|----------|------|---------|----------|
| CFR_PROXY_DATA_LOADING_ANALYSIS.md | 24 KB | Complete analysis | 10 |
| CFR_QUICK_REFERENCE.md | 5.9 KB | Quick lookup | 18 |
| CFR_FILES_AND_FUNCTIONS.md | 11 KB | Function reference | 15 |
| CFR_ANALYSIS_INDEX.md | This file | Navigation guide | 12 |
| **TOTAL** | **~41 KB** | **Comprehensive coverage** | **55+** |

---

## Next Steps

### To Use This Documentation
1. **Start with**: CFR_QUICK_REFERENCE.md for quick answers
2. **Deep dive**: CFR_PROXY_DATA_LOADING_ANALYSIS.md for understanding
3. **Reference**: CFR_FILES_AND_FUNCTIONS.md for implementation details
4. **Navigate**: This index when looking for specific topics

### To Work with Custom Data
1. Check PICKLE_TO_NETCDF_README.md for conversion steps
2. Use convert_pickle_to_netcdf.py for conversion
3. Load with ProxyDatabase().load_nc() or fetch()
4. Configure filtering/annualization in lmr_configs.yml

### To Understand the Full Pipeline
1. Read Section 1 of CFR_PROXY_DATA_LOADING_ANALYSIS.md
2. Follow the function call flow in CFR_FILES_AND_FUNCTIONS.md
3. Review complete example in CFR_QUICK_REFERENCE.md
4. Study prep_da_cfg() in reconjob.py (line 802)

---

## Summary

This comprehensive analysis provides:

✓ **How CFR loads proxy data** - Complete technical pipeline
✓ **Supported formats** - 6+ input formats with auto-detection
✓ **Expected schema** - ProxyRecord and ProxyDatabase structure
✓ **Custom data examples** - Loading from CSV, JSON, Pickle, NetCDF
✓ **NetCDF details** - File structure and format specifications
✓ **ReconJob pipeline** - Complete data assimilation workflow
✓ **Code examples** - Ready-to-use code snippets
✓ **Function reference** - All 40+ key functions documented
✓ **Configuration guide** - YAML file structure and parameters
✓ **Proxy types** - Complete list of 30+ supported types

---

## Citation

If using this analysis in academic work, cite as:
"CFR Proxy Data Loading Analysis - Very Thorough Investigation (2024)"

Generated through systematic examination of CFR source code from:
https://github.com/fzhu2e/cfr

---

## Contact & Support

For questions about:
- **CFR library**: See https://fzhu2e.github.io/cfr/
- **PAGES2k data**: See https://www.ncei.noaa.gov/products/paleoclimatology-data
- **LMRv2**: See https://github.com/tanaya-g/LMR_reproduce
- **This analysis**: Check the referenced source files

---

**Document Generated**: December 16, 2024  
**CFR Version Analyzed**: Latest (master branch)  
**Analysis Type**: Very Thorough  
**Status**: Complete

# Presto-Viz CFR Data Fixes

## CRITICAL: Two Fixes Required in presto-viz Repository!

There are **TWO bugs** in presto-viz that prevent CFR data from working:

1. **Script 1 Bug**: Dimension ordering (causes merge error)
2. **Script 2 Bug**: Missing CFR detection (causes NameError)

Both must be fixed for visualization to work!

---

## Fix 1: Script 1 Dimension Bug (APPLIED ✓)

### Status: Applied to presto-viz main branch

This fix has been applied. If you still see dimension errors, verify the fix is in your presto-viz repository.

---

## Fix 2: Script 2 CFR Detection Bug (NEW - MUST APPLY)

### Problem
Script 2 (`2_make_maps_and_ts.py`) doesn't detect CFR datasets, causing:
```
NameError: name 'dataset_txt' is not defined
```

### Fix for 2_make_maps_and_ts.py

**Around lines 48-50, find:**
```python
if   'holocene_da' in data_dir: dataset_txt = 'daholocene'; version_txt = data_dir.split('_holocene_da')[0].split('/')[-1]
elif 'graph_em'    in data_dir: dataset_txt = 'graphem';    version_txt = data_dir.split('_graph_em')[0].split('/')[-1]
```

**Replace with:**
```python
if   'holocene_da' in data_dir:
    dataset_txt = 'daholocene'; version_txt = data_dir.split('_holocene_da')[0].split('/')[-1]
elif 'graph_em' in data_dir:
    dataset_txt = 'graphem';    version_txt = data_dir.split('_graph_em')[0].split('/')[-1]
else:
    dataset_txt = 'cfr';        version_txt = data_dir.rstrip('/').split('/')[-1]
```

**Quick Apply:** See `presto-viz-script2-fix.patch` in this repo.

---

## Original Fix 1 Documentation

## IMPORTANT: You Must Apply This Fix to presto-viz Repository First!

The workflow is currently using `@main` temporarily, but **it will still fail with the dimension error** until you apply this fix to the presto-viz repository.

## Quick Start

1. Navigate to your presto-viz repository
2. Apply the patch file from this repo: `presto-viz-cfr-fix.patch`
3. Push to either `main` or create the `fix/cfr-dimension-order` branch
4. Update LMR2's visualize.yml to reference the fixed branch

## Problem
The presto-viz script `1_format_data_daholocene_graphem.py` has a bug when processing CFR/LMR2 data. It incorrectly swaps the time and ensemble dimensions, causing the ensemble mean to be computed across the time axis instead of the ensemble axis.

This results in the error:
```
ValueError: conflicting sizes for dimension 'age':
  length 2001 on 'tas_spatial_mean' and length 1 on 'tas_global_mean'
```

## Root Cause
After reshaping CFR data, the script creates:
- `var_global_members` with shape `(method, time, ens)` = `(1, 2001, 1)`
- Then computes: `var_global_mean = np.mean(var_global_members, axis=1)`
- This averages along **axis=1 (time)** instead of **axis=2 (ensemble)**
- Result: shape `(1, 1)` instead of expected `(1, 2001)`

## Solution

Apply this fix to `DaveEdge1/presto-viz/1_format_data_daholocene_graphem.py`:

### Lines 174-178 (approximately)

**Before:**
```python
if var_spatial_members.ndim == 4:  # (ens, time, lat, lon)
    var_spatial_members = np.swapaxes(var_spatial_members, 0, 1)  # -> (time, ens, lat, lon)
    var_spatial_members = np.expand_dims(var_spatial_members, axis=0)  # Add method dimension

if var_global_members.ndim == 2:  # (ens, time)
    var_global_members = np.swapaxes(var_global_members, 0, 1)  # -> (time, ens)
    var_global_members = np.expand_dims(var_global_members, axis=0)  # Add method dimension
```

**After:**
```python
if var_spatial_members.ndim == 4:  # (ens, time, lat, lon)
    var_spatial_members = np.expand_dims(var_spatial_members, axis=0)  # -> (method, ens, time, lat, lon)

if var_global_members.ndim == 2:  # (ens, time)
    var_global_members = np.expand_dims(var_global_members, axis=0)  # -> (method, ens, time)
```

## How to Apply

1. Clone the presto-viz repository:
   ```bash
   git clone https://github.com/DaveEdge1/presto-viz.git
   cd presto-viz
   ```

2. Create a fix branch:
   ```bash
   git checkout -b fix/cfr-dimension-order
   ```

3. Apply the changes above to `1_format_data_daholocene_graphem.py`

4. Commit and push:
   ```bash
   git add 1_format_data_daholocene_graphem.py
   git commit -m "Fix CFR data dimension order for ensemble averaging"
   git push -u origin fix/cfr-dimension-order
   ```

5. The LMR2 workflow has been updated to use this fix branch automatically

## Explanation

The fix removes the unnecessary `swapaxes` operations. When we have CFR data with shape `(ens, time)`, we only need to add the method dimension at axis=0, which gives us `(method, ens, time)` directly. The original code was swapping axes first, creating `(time, ens)`, then expanding to `(method, time, ens)`, which put the dimensions in the wrong order.

The correct dimension order is:
- `tas_global_members`: `(method, ens_global, age)`
- `tas_spatial_members`: `(method, ens_spatial, age, lat, lon)`

This allows the mean computation `np.mean(var_global_members, axis=1)` to correctly average across the ensemble dimension (axis=1), producing the expected shape `(method, age)`.

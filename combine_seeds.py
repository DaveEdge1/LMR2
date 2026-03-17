"""
combine_seeds.py  —  merge all job_r*_recon.nc seed files into combined_recon.nc

Runs in a fresh Docker container *after* the reconstruction container exits,
so peak memory here is only the data being combined (not the full CFR state).

Memory strategy: open each seed file lazily with xarray's dask backend and
write the combined dataset in time-chunks so only one chunk is resident at a
time.  This keeps peak RAM proportional to chunk_size rather than n_seeds * T.

Combined layout (expected by presto-viz Script 1):
  tas    (time, n_seeds, lat, lon)  – one spatial mean per seed
  tas_gm (time, total_ens)          – all ensemble members across all seeds
"""
import glob
import os
import xarray as xr

RECON_DIR  = '/recons'
CHUNK_TIME = 50   # time steps materialised at once during write (~few MB/chunk)
OUT_PATH   = os.path.join(RECON_DIR, 'combined_recon.nc')

files = sorted(glob.glob(os.path.join(RECON_DIR, 'job_r*_recon.nc')))
if not files:
    raise RuntimeError(f'No job_r*_recon.nc files found in {RECON_DIR}')
print(f'Combining {len(files)} seed file(s): {[os.path.basename(f) for f in files]}')

tas_list    = []
tas_gm_list = []
for f in files:
    # chunks= enables dask lazy loading; data stays on disk until written
    ds = xr.open_dataset(f, chunks={'time': CHUNK_TIME})
    tas_list.append(ds['tas'])     # (time, lat, lon)
    tas_gm_list.append(ds['tas_gm'])  # (time, ens_per_seed)

# tas: concat creates (n_seeds, time, lat, lon); transpose to (time, n_seeds, lat, lon)
tas    = xr.concat(tas_list,    dim='ens').transpose('time', 'ens', 'lat', 'lon')
# tas_gm: concat along existing ens dim → (time, total_ens)
tas_gm = xr.concat(tas_gm_list, dim='ens')

# to_netcdf streams chunks to disk without materialising the full array
xr.Dataset({'tas': tas, 'tas_gm': tas_gm}).to_netcdf(OUT_PATH)

print(f'combined_recon.nc written: {OUT_PATH}')
print(f'  tas    {dict(tas.sizes)}')
print(f'  tas_gm {dict(tas_gm.sizes)}')

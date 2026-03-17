import cfr
import yaml
import os

job_cfg = cfr.ReconJob()

# Load base config (all static settings baked into the image)
with open('lmr_configs.yml') as f:
    base_config = yaml.safe_load(f) or {}

# Merge user overrides if present (mounted from workflow as /app/user_config.yml)
user_config_path = 'user_config.yml'
if os.path.exists(user_config_path):
    with open(user_config_path) as f:
        user_overrides = yaml.safe_load(f) or {}
    base_config.update(user_overrides)
    print(f'Loaded user overrides: {list(user_overrides.keys())}')

# Write merged config and run
with open('/tmp/merged_config.yml', 'w') as f:
    yaml.dump(base_config, f)

job_cfg.run_da_cfg('/tmp/merged_config.yml', run_mc=True, verbose=True)

# ── Post-processing: combine all seed runs into combined_recon.nc ─────────────
# cfr.ReconRes discovers all job_r*_recon.nc files in /recons/ and concatenates
# them along the ensemble dimension, giving the visualizer the full spread.
print('\nPost-processing: combining seed runs with cfr.ReconRes...')
try:
    recon = cfr.ReconRes('/recons/')
    recon.load(['tas', 'tas_gm'])
    # After load:
    #   recon.da['tas']    -> (time, n_seeds, lat, lon)  one spatial mean per seed
    #   recon.da['tas_gm'] -> (time, total_ens)          all ensemble members across seeds

    import xarray as xr
    combined = xr.Dataset(
        {
            'tas':    recon.da['tas'],
            'tas_gm': recon.da['tas_gm'],
        }
    )
    out_path = '/recons/combined_recon.nc'
    combined.to_netcdf(out_path)

    n_seeds  = combined['tas'].sizes.get('ens',  combined['tas'].shape[1])
    n_ens_gm = combined['tas_gm'].sizes.get('ens', combined['tas_gm'].shape[1])
    print(f'  combined_recon.nc written to {out_path}')
    print(f'  Spatial:     {n_seeds} seed means  {dict(combined["tas"].sizes)}')
    print(f'  Global mean: {n_ens_gm} members    {dict(combined["tas_gm"].sizes)}')

except Exception as e:
    print(f'Warning: failed to combine seed runs: {e}')
    print('Visualization will use only the first seed file.')

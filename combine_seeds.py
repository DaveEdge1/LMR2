import cfr
import xarray as xr

print('Combining seed runs with cfr.ReconRes...')
recon = cfr.ReconRes('/recons/')
recon.load(['tas', 'tas_gm'])

combined = xr.Dataset({
    'tas':    recon.da['tas'],
    'tas_gm': recon.da['tas_gm'],
})
combined.to_netcdf('/recons/combined_recon.nc')
print(f'combined_recon.nc written to /recons/combined_recon.nc')
print(f'  Spatial:     {dict(combined["tas"].sizes)}')
print(f'  Global mean: {dict(combined["tas_gm"].sizes)}')

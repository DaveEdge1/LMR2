import cfr
import yaml
import os
import math
import gc
import time
import numpy as np
import pandas as pd
import xarray as xr
import json
import re

# Maximum ensemble members per sequential run.
# Above this, nens is capped here and recon_seeds is expanded so that
# total ensemble count (nens × n_seeds) stays the same.
# At the current prior regrid (42×63), nens=100 uses ~2 GB on top of the
# ~5 GB prior download, comfortably within the 7 GB free-tier runner.
NENS_BATCH = 100

# Number of years per chunk when running the reconstruction.
# Keeps peak memory below the 7 GB free-tier runner limit by avoiding
# a single giant (nt, nens, nlat, nlon) array for the full period.
CHUNK_YEARS = 500

# Minimum observation error variance (floor on PSMmse).
# Prevents kdenom = varye + ob_err → 0 when a proxy has near-zero MSE
# (e.g. constant-value records, or perfectly-fitted OLS with few points).
MIN_R = 0.01

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

# ── Validate recon_period early (before any expensive work) ──────────────────
# Without this guard a swapped/equal recon_period silently produces zero chunks
# and the workflow fails much later with a generic "no reconstruction
# results" message.
_rp = base_config.get('recon_period')
if not isinstance(_rp, (list, tuple)) or len(_rp) < 2:
    raise ValueError(
        f'recon_period must be [start_year, end_year]; got {_rp!r}')
_rp_start, _rp_end = int(_rp[0]), int(_rp[-1])
if _rp_end < _rp_start:
    raise ValueError(
        f'recon_period end year ({_rp_end}) must be >= start year '
        f'({_rp_start}); swap your endpoints')
if _rp_end - _rp_start < 1:
    raise ValueError(
        f'recon_period must span at least 2 years for variance / CE '
        f'computations; got [{_rp_start}, {_rp_end}]')

# ── Auto-batch large ensemble sizes ──────────────────────────────────────────
# Goal: total ensemble members (nens × n_seeds) stays constant. When
# nens > NENS_BATCH we cap nens at NENS_BATCH and expand recon_seeds so the
# product is preserved. The expansion must produce *unique* seed values —
# duplicates run identical realizations and distort the mean.
nens  = base_config.get('nens', NENS_BATCH)
seeds = list(base_config.get('recon_seeds', [1]))

if nens > NENS_BATCH:
    n_batches = math.ceil(nens / NENS_BATCH)
    needed = (n_batches - 1) * len(seeds)
    # Generate sequential seeds starting just after the largest existing one.
    # Sequential RNG seeds are statistically independent, so this is no worse
    # than the prior scattered scheme and is collision-free by construction.
    next_seed = max(seeds) + 1
    extra_seeds = list(range(next_seed, next_seed + needed))
    base_config['nens']        = NENS_BATCH
    base_config['recon_seeds'] = seeds + extra_seeds
    total_members = NENS_BATCH * len(base_config['recon_seeds'])
    print(f'Auto-batching: nens={nens} > {NENS_BATCH}; '
          f'running {n_batches} batches of {NENS_BATCH} '
          f'({len(base_config["recon_seeds"])} unique seeds, '
          f'{total_members} total ensemble members)')
else:
    print(f'nens={nens} <= {NENS_BATCH}; running {len(seeds)} seed(s) as configured')

# Write merged config
with open('/tmp/merged_config.yml', 'w') as f:
    yaml.dump(base_config, f)

# ── Phase 1: prep (load data, calibrate PSMs) ────────────────────────────────
# Check if the proxy database pickle is already a cfr.ProxyDatabase object
# (e.g. presto2k_pdb.pkl) rather than a DataFrame. If so, load it directly
# and patch load_proxydb to skip the reload (prep_da_cfg always calls it).
import pickle as _pkl
_pdb_path = base_config.get('proxydb_path', '')
if os.path.exists(_pdb_path):
    with open(_pdb_path, 'rb') as _f:
        _pdb_obj = _pkl.load(_f)
    if isinstance(_pdb_obj, cfr.proxy.ProxyDatabase):
        print(f'Pre-loaded ProxyDatabase from {_pdb_path} '
              f'({len(_pdb_obj.records)} records)')
        job_cfg.proxydb = _pdb_obj
        # Patch load_proxydb to no-op so prep_da_cfg doesn't overwrite
        job_cfg.load_proxydb = lambda *a, **kw: None
    del _pdb_obj

job_cfg.prep_da_cfg('/tmp/merged_config.yml', verbose=True)

# ── Phase 1.5: interpretation against PSM ────────────────────────────────────
# Any record may enter, but a calibrated record is dropped when its metadata
# contradicts the PSM it was calibrated with:
#   - it has interpretations, and none names a variable the PSM uses (a
#     salinity coral, sea-ice sodium, or a precipitation-isotope-only record
#     under a tas PSM; Bilinear TRW takes a temperature or a hydroclimate
#     interpretation);
#   - an interpretation that names a PSM variable gives a direction, and no
#     calibration season gives a slope of that sign. cfr picks the season by
#     adjusted R2 alone; when its pick has the wrong sign, the record is
#     recalibrated on the best season that has the right one.
# A record with no interpretation whose variable is itself a climate variable
# (a "precipitation" or "PDSI" reconstruction) is treated as interpreted as
# that variable, positively. Any other record with no interpretation is left
# to its calibration. Interpretations
# come from lipd_to_pdb.py's paleoData_interpretations column; a pre-built
# cfr.ProxyDatabase has none, and the check is skipped.
INTERP_CLASSES = [
    # (pattern on the lowercased variable, PSM variable, sign of the
    #  variable relative to it); first match wins.
    (r'isotope|deuterium|excess|d18o|dd$', None, None),
    (r'temp|^sst$|^t$|degree.?day', 'tas', 1),
    (r'vpd|vapou?r.?pressure.?deficit|aridity|evapo', 'pr', -1),
    (r'drought', 'pr', None),
    (r'precip|moisture|pdsi|spei|^spi$|humid|^p-e$|^p_e$|rain|streamflow|runoff|wet', 'pr', 1),
]


def _interp_class(variable):
    v = str(variable).lower().strip()
    for pat, var, sign in INTERP_CLASSES:
        if re.search(pat, v):
            return var, sign
    return None, None


def _direction(d):
    d = str(d or '').lower().strip()
    if d in ('positive', 'increase', 'positively correlated'):
        return 1
    if d in ('negative', 'decrease', 'negatively correlated'):
        return -1
    return None


def _signs_ok(model, expected):
    return all(var in model.params and np.sign(model.params[var]) == e for var, e in expected.items())


def _refit_signed(pobj, expected, seasons, calib_period):
    """Recalibrate on the best season (by adjusted R2, as cfr chooses) whose
    slopes have the expected signs. cfr's season search ignores sign, so a
    winter or previous-year season with a negative response can beat a
    positive summer one. Returns the season, or None (the PSM is then left
    as cfr fitted it)."""
    seasons = seasons if isinstance(seasons[0], list) else [seasons]
    bilinear = type(pobj.psm).__name__ == 'Bilinear'
    combos = [(a, b) for a in seasons for b in seasons] if bilinear else [(a,) for a in seasons]
    fit = (lambda c: pobj.psm.calibrate(season_list1=[c[0]], season_list2=[c[1]], calib_period=calib_period)) \
        if bilinear else (lambda c: pobj.psm.calibrate(season_list=[c[0]], calib_period=calib_period))
    original = pobj.psm.calib_details['seasonality']
    best = None
    for c in combos:
        fit(c)
        m = pobj.psm.model
        if m is not None and _signs_ok(m, expected) and (best is None or m.rsquared_adj > best[0]):
            best = (m.rsquared_adj, c)
    fit(best[1] if best else (original if bilinear else (original,)))
    if best is None:
        return None
    pobj.R = pobj.psm.calib_details['PSMmse']
    pobj.pseudo = pobj.psm.forward()
    return best[1]


def screen_interpretations(job, df, clim_dict, out_csv):
    interp = dict(zip(df['paleoData_pages2kID'].astype(str), df['paleoData_interpretations']))
    season_dict = job.configs.get('ptype_season_dict') or {}
    calib_period = job.configs.get('psm_calib_period', [1850, 2015])
    rows = []
    for pid, pobj in job.proxydb.records.items():
        if 'calibrated' not in pobj.tags:
            continue
        psm_vars = list(clim_dict.get(pobj.ptype, ['tas']))
        ii = json.loads(interp.get(str(pid)) or '[]')
        classes = [(i['variable'],) + _interp_class(i['variable']) + (_direction(i['direction']),) for i in ii]
        implied = False
        if not classes:
            var, sign = _interp_class(pobj.value_name or '')
            if var is not None:
                classes, implied = [(str(pobj.value_name), var, sign, 1)], True
        matched = [c for c in classes if c[1] in psm_vars]
        status, detail = 'pass', 'interpretation implied by variable name;' if implied else ''
        season0 = pobj.psm.calib_details['seasonality']
        if not classes:
            status = 'uninterpreted'
        elif not matched:
            status, detail = 'drop_interpretation', ';'.join(sorted({c[0] for c in classes}))
        else:
            # expected sign of the slope on each PSM variable: the
            # interpretation's direction times the sign of the interpreted
            # variable relative to it; conflicting directions are not checked
            expected = {}
            for var in psm_vars:
                exp = {c[3] * c[2] for c in matched if c[1] == var and c[2] is not None and c[3] is not None}
                if len(exp) == 1:
                    expected[var] = exp.pop()
                elif len(exp) > 1:
                    detail += f'{var}: conflicting directions, not checked;'
            if expected and not _signs_ok(pobj.psm.model, expected):
                sn = _refit_signed(pobj, expected, season_dict.get(pobj.ptype, [list(range(1, 13))]), calib_period)
                if sn is None:
                    status = 'drop_direction'
                    detail += 'no season gives the interpreted sign;'
                else:
                    status = 'pass_reseasoned'
                    detail += f'season {season0} -> {list(sn) if len(sn) > 1 else sn[0]};'
        if status.startswith('drop'):
            pobj.tags.discard('calibrated')
        params = pobj.psm.model.params
        rows.append(dict(pid=pid, ptype=pobj.ptype, psm_vars='+'.join(psm_vars), status=status, detail=detail,
                         interpretations='; '.join(f'{c[0]} ({c[3] if c[3] is not None else "?"})' for c in classes),
                         fitR2adj=pobj.psm.calib_details['fitR2adj'],
                         **{f'slope_{v}': params.get(v, np.nan) for v in ('tas', 'pr')}))
    tab = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    tab.to_csv(out_csv, index=False)
    print('Interpretation against PSM:', tab.status.value_counts().to_dict(), f'-> {out_csv}')
    return tab


_df = pd.read_pickle(_pdb_path) if os.path.exists(_pdb_path) else None
if base_config.get('interpretation_screen', True) and isinstance(_df, pd.DataFrame) \
        and 'paleoData_interpretations' in _df:
    _clim = dict(base_config.get('ptype_clim_dict') or {})
    screen_interpretations(job_cfg, _df, _clim,
                           os.path.join(base_config.get('save_dirpath', '/recons'), 'psm_screen.csv'))
else:
    print('Interpretation against PSM: skipped (no paleoData_interpretations column, '
          'or interpretation_screen: false)')
del _df

# ── Phase 2: enforce minimum R floor ─────────────────────────────────────────
# PSMmse=0 → ob_err=0, combined with varye=0 (flat PSM slope) → kdenom=0
# → Kalman gain blows up. r_floor: relative (default) also floors R at 1% of
# each record's own variance, so its noise standard deviation is at least a
# tenth of its variability whatever its units; the fixed MIN_R stays as a
# lower bound. r_floor: fixed keeps only MIN_R.
r_floor = base_config.get('r_floor', 'relative')
if r_floor not in ('relative', 'fixed'):
    raise ValueError(f"r_floor must be 'relative' or 'fixed', not {r_floor!r}")
n_floor = 0
for pid, pobj in job_cfg.proxydb.records.items():
    r_val = getattr(pobj, 'R', None)
    if r_val is None or not np.isfinite(r_val):
        continue
    floor = MIN_R
    if r_floor == 'relative':
        floor = max(floor, 0.01 * float(np.nanvar(np.asarray(pobj.value, dtype=float))))
    if r_val < floor:
        pobj.R = floor
        n_floor += 1
if n_floor:
    print(f'R floor ({r_floor}): raised {n_floor} record(s)')

# ── Phase 2.5: Auto-trim recon start year based on proxy coverage ───────────
# cfr iterates over every year in recon_period regardless of proxy availability.
# Years with zero/few proxies produce a flat reconstruction that just equals the
# prior mean, which is misleading. Trim the start year to where proxy coverage
# reaches a meaningful threshold.
MIN_PROXIES_DEFAULT = 10
min_proxies = base_config.get('min_proxies_for_recon', MIN_PROXIES_DEFAULT)
cfg = job_cfg.configs
recon_period = list(cfg['recon_period'])

if min_proxies > 0 and len(job_cfg.proxydb.records) > 0:
    start_yr, end_yr = int(recon_period[0]), int(recon_period[-1])
    n_years = end_yr - start_yr + 1
    coverage = np.zeros(n_years, dtype=int)
    for pobj in job_cfg.proxydb.records.values():
        t = getattr(pobj, 'time', None)
        if t is None or len(t) == 0:
            continue
        proxy_years = np.unique(np.floor(np.asarray(t, dtype=float)).astype(int))
        proxy_years = proxy_years[(proxy_years >= start_yr) & (proxy_years <= end_yr)]
        coverage[proxy_years - start_yr] += 1

    sufficient = np.where(coverage >= min_proxies)[0]
    if len(sufficient) == 0:
        print(f'WARNING: No year has >= {min_proxies} proxies '
              f'(max coverage: {int(coverage.max())}). '
              f'Running full period {start_yr}-{end_yr} as configured.')
    else:
        new_start = start_yr + int(sufficient[0])
        if new_start > start_yr:
            print(f'Auto-trim: proxy coverage >= {min_proxies} begins at year {new_start} '
                  f'(was {start_yr}). Max coverage: {int(coverage.max())} proxies. '
                  f'Updating recon_period to [{new_start}, {end_yr}].')
            recon_period[0] = new_start
            cfg['recon_period'] = recon_period
        else:
            print(f'Auto-trim: proxy coverage >= {min_proxies} at start year {start_yr}; '
                  f'no trim needed.')

# ── Phase 3: run DA (chunked to stay within 7 GB runner memory) ──────────────
recon_period    = cfg['recon_period']
recon_loc_rad   = cfg['recon_loc_rad']
recon_timescale = cfg.get('recon_timescale', 1)
recon_seeds     = cfg.get('recon_seeds', [0])
assim_frac      = cfg.get('assim_frac', 0.75)
compress_params = cfg.get('compress_params', {'zlib': True})
output_full_ens = cfg.get('output_full_ens', False)
output_indices  = cfg.get('output_indices', None)
save_dirpath    = cfg.get('save_dirpath', '/recons')

os.makedirs(save_dirpath, exist_ok=True)

start_yr = int(recon_period[0])
end_yr   = int(recon_period[-1])
total_years = end_yr - start_yr + 1

# Build chunk boundaries
chunk_starts = list(range(start_yr, end_yr + 1, CHUNK_YEARS))
chunks = [(cs, min(cs + CHUNK_YEARS - 1, end_yr)) for cs in chunk_starts]
print(f'Chunked reconstruction: {len(chunks)} chunk(s) of up to {CHUNK_YEARS} years '
      f'over [{start_yr}, {end_yr}]')

t_s = time.time()

for seed in recon_seeds:
    print(f'>>> seed: {seed} | max: {recon_seeds[-1]}')

    # cfr's split_proxydb only adds 'assim'/'eval' tags and never removes
    # them, so without this a record drawn for assimilation by any earlier
    # seed stays assimilated: by the 5th seed of a job nearly every record is
    # assimilated and the eval set overlaps it (cfr 2025.7.28; its own
    # run_da_mc has the same loop). Clear only these two tags; cfr's
    # clear_proxydb_tags() would also drop 'calibrated', which the split
    # filters on.
    for _pobj in job_cfg.proxydb.records.values():
        _pobj.tags = set(_pobj.tags) - {'assim', 'eval'}
    job_cfg.split_proxydb(seed=seed, assim_frac=assim_frac, verbose=False)

    chunk_files = []
    for ci, (c_start, c_end) in enumerate(chunks):
        print(f'  chunk {ci+1}/{len(chunks)}: [{c_start}, {c_end}]')

        job_cfg.run_da(
            recon_period=[c_start, c_end],
            recon_loc_rad=recon_loc_rad,
            recon_timescale=recon_timescale,
            nens=cfg.get('nens', NENS_BATCH),
            seed=seed,
            # Disable trim_prior: cfr would otherwise restrict the prior
            # sample pool to years within the chunk's recon_period, which
            # is empty for chunks outside the prior's time range (e.g.
            # chunk [0, 499] with a CCSM4 prior covering 850-1850).
            trim_prior=False,
            verbose=False,
        )

        chunk_path = os.path.join(save_dirpath, f'job_r{seed:02d}_chunk{ci:03d}.nc')
        job_cfg.save_recon(
            chunk_path,
            compress_params=compress_params,
            mark_assim_pids=(ci == 0),
            verbose=False,
            output_full_ens=output_full_ens,
            grid='prior',
            output_indices=output_indices,
        )
        chunk_files.append(chunk_path)

        # Free the large arrays before the next chunk
        job_cfg.recon_fields = {}
        if hasattr(job_cfg, 'da_solver'):
            del job_cfg.da_solver
        gc.collect()

    # Concatenate chunk files into the final per-seed NetCDF
    final_path = os.path.join(save_dirpath, f'job_r{seed:02d}_recon.nc')
    if len(chunk_files) == 1:
        os.rename(chunk_files[0], final_path)
    else:
        datasets = [xr.open_dataset(f) for f in chunk_files]
        combined = xr.concat(datasets, dim='time')
        # Preserve attrs (pids_assim/pids_eval) from the first chunk
        combined.attrs = datasets[0].attrs
        for ds in datasets:
            ds.close()
        encoding = {v: compress_params for v in combined.data_vars}
        combined.to_netcdf(final_path, encoding=encoding)
        combined.close()
        for f in chunk_files:
            os.remove(f)

    print(f'  saved: {final_path}')
    gc.collect()

t_used = time.time() - t_s
print(f'>>> DONE! Total time spent: {t_used/60:.2f} mins.')

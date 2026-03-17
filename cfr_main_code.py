import cfr
import yaml
import os
import math

# Maximum ensemble members per sequential run.
# Above this, nens is capped here and recon_seeds is expanded so that
# total ensemble count (nens × n_seeds) stays the same.
# At the current prior regrid (42×63), nens=100 uses ~2 GB on top of the
# ~5 GB prior download, comfortably within the 7 GB free-tier runner.
NENS_BATCH = 100

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

# ── Auto-batch large ensemble sizes ──────────────────────────────────────────
# If nens > NENS_BATCH, split into ceil(nens / NENS_BATCH) sequential batches
# by capping nens and expanding recon_seeds.  Seeds are offset per batch so
# each batch draws a different random subset of the prior.
# Total ensemble count (nens × n_seeds) is preserved.
nens  = base_config.get('nens', NENS_BATCH)
seeds = list(base_config.get('recon_seeds', [1]))

if nens > NENS_BATCH:
    n_batches = math.ceil(nens / NENS_BATCH)
    max_seed  = max(seeds)
    extra_seeds = [s + b * max_seed for b in range(1, n_batches) for s in seeds]
    base_config['nens']         = NENS_BATCH
    base_config['recon_seeds']  = seeds + extra_seeds
    print(f'Auto-batching: nens={nens} > {NENS_BATCH}; '
          f'running {n_batches} batches of {NENS_BATCH} '
          f'({len(base_config["recon_seeds"])} total seeds, '
          f'{NENS_BATCH * len(base_config["recon_seeds"])} total ensemble members)')
else:
    print(f'nens={nens} <= {NENS_BATCH}; running {len(seeds)} seed(s) as configured')

# Write merged config and run
with open('/tmp/merged_config.yml', 'w') as f:
    yaml.dump(base_config, f)

job_cfg.run_da_cfg('/tmp/merged_config.yml', run_mc=True, verbose=True)

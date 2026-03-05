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

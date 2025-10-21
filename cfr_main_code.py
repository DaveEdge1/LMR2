import cfr

job_cfg = cfr.ReconJob()
job_cfg.run_da_cfg('lmr_configs.yml', run_mc=True, verbose=True)

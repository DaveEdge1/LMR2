import cfr

job_cfg = cfr.ReconJob()
job_cfg.run_da_cfg('configs.yml', run_mc=True, verbose=True)

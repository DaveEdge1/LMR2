[![DOI](https://zenodo.org/badge/1078431321.svg)](https://doi.org/10.5281/zenodo.17819391)  

## 3-Component Architecture Example

By [David Edge](https://orcid.org/0000-0001-6938-2850), [Tanaya Gondhalekar](https://orcid.org/0009-0004-2440-3266), & [Julien Emile-Geay](https://orcid.org/0000-0001-5920-4751).

[PReSto](paleopresto.com) lowers the barriers to utilyzing, reproducing, and customizing paleoclimate reconstructions. 

This repository showcases the use of containers, paramter files (yaml), and GitHub Actions to reproduce and customize the Last Millennium Reanalysis, version 2.1 (Tardif et al, 2019), which used the offline data assimilation method of Hakim et al. (2016) together with the PAGES 2k database, version 2.0.0. More information on reproducing LMRv2 interactively can be found [here](https://github.com/tanaya-g/LMR_reproduce).

### How to use this repository

#### Clone and use   
You can use a clone of this repo to run LMRv2 yourself. Simply
- clone the repo
- make any edits you would like to the reconstruction configs (lmr_configs.yml) following the instructions from [cfr](https://fzhu2e.github.io/cfr/ug-lmr.html)
- the Run CFR action
  - automatically initiated when changes to lmr_configs.yml are pushed
  - can be manually initiated on the Actions tab of the cloned repo
- reconstruction data are saved for 30 days

### Note on repository structure

The Dockerfile and associated workflow file show the construction of the container where the computation takes place. This code is kept within this repo to show the provenance of the container environment. Altering the container image allows for future updates to the reconstruction methods but requires utilyzing your own container registry and editing the repository secrets used to access it.

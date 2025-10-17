# Docker Usage Guide for LMR2 Project

This guide explains how to build and use the Docker container for the LMR2 Climate Field Reconstruction project.

## Prerequisites

- Docker installed (version 20.10 or later recommended)
- Docker Compose (optional, for easier management)
- At least 8GB of free disk space for the image
- At least 4GB of RAM available for the container

## Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
# Build and start the container
docker-compose up -d

# Enter the container
docker-compose exec lmr2-app bash

# Run your script inside the container
python lmr_reproduce.py

# Stop the container
docker-compose down
```

### Option 2: Using Docker Commands Directly

```bash
# Build the image
docker build -t lmr2-cfr:latest .

# Or use the build script
chmod +x docker-build.sh
./docker-build.sh

# Run the container interactively
docker run -it --rm lmr2-cfr:latest

# Run with mounted data directories
docker run -it --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/prev_data:/app/prev_data \
  -v $(pwd)/cases:/app/cases \
  -v $(pwd)/recons:/app/recons \
  lmr2-cfr:latest
```

## Building the Image

### Standard Build

```bash
docker build -t lmr2-cfr:latest .
```

### Build with BuildKit (Faster, Better Caching)

```bash
DOCKER_BUILDKIT=1 docker build -t lmr2-cfr:latest .
```

### Build with a Custom Tag

```bash
docker build -t lmr2-cfr:v1.0 .
```

## Running Your Application

### Interactive Shell

Start a bash shell inside the container with the conda environment activated:

```bash
docker run -it --rm lmr2-cfr:latest
```

### Run Your Script Directly

```bash
docker run -it --rm lmr2-cfr:latest conda run -n cfr-env python lmr_reproduce.py
```

### Run with GPU Support (if available)

```bash
docker run -it --rm --gpus all lmr2-cfr:latest
```

## Volume Mounts

Mount local directories to persist data and share files between host and container:

```bash
docker run -it --rm \
  -v $(pwd)/prev_data:/app/prev_data \
  -v $(pwd)/cases:/app/cases \
  -v $(pwd)/recons:/app/recons \
  lmr2-cfr:latest
```

**Important:** Make sure these directories exist on your host system before mounting.

## Environment Variables

You can pass environment variables to control computational resources:

```bash
docker run -it --rm \
  -e OMP_NUM_THREADS=8 \
  -e NUMEXPR_MAX_THREADS=8 \
  -e NUMBA_NUM_THREADS=8 \
  lmr2-cfr:latest
```

## Resource Limits

### CPU Limits

```bash
docker run -it --rm --cpus="4" lmr2-cfr:latest
```

### Memory Limits

```bash
docker run -it --rm --memory="8g" lmr2-cfr:latest
```

### Combined

```bash
docker run -it --rm \
  --cpus="4" \
  --memory="8g" \
  lmr2-cfr:latest
```

## Troubleshooting

### Build Fails During Package Installation

If conda package installation fails:

1. Check internet connectivity
2. Try clearing Docker build cache: `docker builder prune`
3. Rebuild without cache: `docker build --no-cache -t lmr2-cfr:latest .`

### Container Runs Out of Memory

Increase Docker's memory allocation:
- Docker Desktop: Settings → Resources → Memory
- Or use `--memory` flag when running

### Permission Issues with Mounted Volumes

On Linux, you may need to run with the same user ID:

```bash
docker run -it --rm \
  --user $(id -u):$(id -g) \
  -v $(pwd)/data:/app/data \
  lmr2-cfr:latest
```

### Verify Environment Inside Container

```bash
docker run -it --rm lmr2-cfr:latest conda run -n cfr-env python -c "
import numpy as np
import pandas as pd
import xarray as xr
import cfr
print('All imports successful!')
print(f'CFR version: {cfr.__version__}')
"
```

## Advanced Usage

### Save Container State

If you've made changes inside a running container and want to save them:

```bash
# Get container ID
docker ps

# Commit changes to a new image
docker commit <container_id> lmr2-cfr:modified
```

### Export/Import Images

Export the image to share with others:

```bash
docker save lmr2-cfr:latest | gzip > lmr2-cfr-latest.tar.gz
```

Import on another machine:

```bash
docker load < lmr2-cfr-latest.tar.gz
```

### Multi-Stage Build for Smaller Images

For production, consider creating a multi-stage build that separates build dependencies from runtime dependencies.

## Best Practices

1. **Use .dockerignore**: Already configured to exclude unnecessary files
2. **Pin versions**: The Dockerfile uses pinned versions for reproducibility
3. **Layer caching**: environment.yml is copied before application code for better cache usage
4. **Clean up**: Use `docker system prune` periodically to clean up unused images and containers
5. **Security**: Consider uncommenting the non-root user section in the Dockerfile for production use

## System Requirements Analysis

Based on your environment.yml, the container includes:

- **Python 3.11** with scientific stack
- **Core libraries**: NumPy, Pandas, xarray, SciPy
- **Climate data**: netCDF4, HDF5 support
- **Geospatial**: Cartopy, GEOS, PROJ
- **Visualization**: Matplotlib, Plotly, Bokeh
- **Distributed computing**: Dask, distributed
- **Jupyter**: JupyterLab and related tools
- **CFR**: Climate Field Reconstruction library

Total image size: Approximately 5-8 GB

## Performance Optimization

### For Faster Builds

```bash
# Use BuildKit
export DOCKER_BUILDKIT=1

# Parallel builds
docker build --build-arg MAKEFLAGS=-j$(nproc) -t lmr2-cfr:latest .
```

### For Runtime Performance

Set appropriate thread counts based on your CPU:

```bash
docker run -it --rm \
  -e OMP_NUM_THREADS=$(nproc) \
  -e NUMEXPR_MAX_THREADS=$(nproc) \
  --cpus="$(nproc)" \
  lmr2-cfr:latest
```

## Support

For issues related to:
- **Docker**: Check Docker documentation
- **CFR package**: Refer to CFR documentation
- **Environment setup**: Review environment.yml and Dockerfile comments

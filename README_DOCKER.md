# Docker Container for LMR2 Climate Field Reconstruction

This repository includes a production-ready Docker container setup for running the LMR2 (Last Millennium Reanalysis) Climate Field Reconstruction analysis.

## Features

- **Comprehensive System Libraries**: All necessary system dependencies for scientific Python packages
- **Pinned Base Image**: Uses `continuumio/miniconda3:24.7.1-0` for reproducibility
- **Optimized Build**: Multi-layer caching, BuildKit support, and size optimization
- **Complete Environment**: Includes all packages from `environment.yml` with conda-forge support
- **Verification Tests**: Built-in tests to ensure all packages work correctly
- **Production Ready**: Includes security considerations and best practices

## System Requirements

### Included System Libraries

The Docker image includes comprehensive system libraries to support the scientific Python stack:

**Build Tools:**
- gcc, g++, gfortran, make, cmake

**Scientific Computing:**
- OpenBLAS, LAPACK (linear algebra)
- HDF5 (hierarchical data format)
- NetCDF (climate/scientific data format)

**Geospatial:**
- GEOS (geometry operations)
- PROJ (cartographic projections)
- GDAL (geospatial data abstraction)
- SpatialIndex (spatial indexing)

**Graphics & Rendering:**
- FreeType, libpng, libjpeg (for matplotlib)

**Compression & Data:**
- zlib, bzip2, lzma, libzip

**Database:**
- MySQL client libraries

**Utilities:**
- git, curl, wget, vim, nano, SSL/TLS support

## Quick Start

### Using Make (Easiest)

```bash
# Show all available commands
make help

# Build the image
make build

# Run with shell access
make shell

# Verify environment
make verify

# Execute lmr_reproduce.py
make exec
```

### Using Docker Compose

```bash
# Build and start
docker-compose up -d

# Enter container
docker-compose exec lmr2-app bash

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Using Docker Directly

```bash
# Build
docker build -t lmr2-cfr:latest .

# Run interactively
docker run -it --rm lmr2-cfr:latest

# Run your script
docker run -it --rm lmr2-cfr:latest conda run -n cfr-env python lmr_reproduce.py
```

## File Structure

```
.
├── Dockerfile              # Main container definition
├── environment.yml         # Conda environment specification
├── docker-compose.yml      # Docker Compose configuration
├── docker-build.sh         # Build script
├── Makefile               # Make commands for easy management
├── .dockerignore          # Files to exclude from build
├── DOCKER_USAGE.md        # Detailed usage documentation
└── README_DOCKER.md       # This file
```

## Key Improvements Over Standard Docker Builds

### 1. Comprehensive System Dependencies

The Dockerfile includes all system libraries needed for:
- **NumPy/SciPy**: BLAS, LAPACK, OpenBLAS for optimized linear algebra
- **NetCDF/HDF5**: Complete support for climate data formats
- **Cartopy/Geospatial**: GEOS, PROJ, GDAL for geographic operations
- **Matplotlib**: FreeType, PNG, JPEG support for visualization
- **Compilation**: Full build toolchain for packages with C extensions

### 2. Build Optimization

- **Layer Caching**: environment.yml copied before code for efficient rebuilds
- **BuildKit**: Modern Docker build system with parallel operations
- **Size Optimization**: Aggressive cleanup of build artifacts and caches
- **Pinned Versions**: Reproducible builds with version-locked base image

### 3. Conda Configuration

```dockerfile
# Strict channel priority for reproducibility
RUN conda config --set channel_priority strict && \
    conda config --set always_yes yes && \
    conda config --prepend channels conda-forge
```

### 4. Comprehensive Verification

The build includes tests for all critical packages:
- Python version
- NumPy, Pandas, xarray
- NetCDF4, SciPy
- Matplotlib, Cartopy
- CFR package itself

### 5. Security Considerations

- Non-root user configuration (optional, commented out)
- Minimal base image
- No unnecessary services running
- Clean removal of temporary files

## Performance Tuning

### CPU/Memory Allocation

Edit `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '8'
      memory: 16G
```

Or use Docker run flags:

```bash
docker run -it --rm --cpus="8" --memory="16g" lmr2-cfr:latest
```

### Thread Configuration

Set environment variables for parallel processing:

```bash
docker run -it --rm \
  -e OMP_NUM_THREADS=8 \
  -e NUMEXPR_MAX_THREADS=8 \
  -e NUMBA_NUM_THREADS=8 \
  lmr2-cfr:latest
```

## Troubleshooting

### Build Issues

**Problem**: Build fails during conda environment creation
**Solution**:
```bash
# Try building without cache
make build-no-cache
# Or
docker build --no-cache -t lmr2-cfr:latest .
```

**Problem**: Network timeout during package download
**Solution**:
- Check internet connectivity
- Try building again (downloads are cached)
- Increase Docker daemon timeout

### Runtime Issues

**Problem**: Import errors for specific packages
**Solution**:
```bash
# Verify environment
make verify
```

**Problem**: Out of memory errors
**Solution**:
- Increase Docker memory allocation
- Use `--memory` flag with higher limit
- Check `docker stats` for current usage

**Problem**: Permission denied on mounted volumes
**Solution**:
```bash
# On Linux, run with matching user ID
docker run -it --rm --user $(id -u):$(id -g) -v $(pwd)/data:/app/data lmr2-cfr:latest
```

## Development Workflow

### Making Changes

1. Modify code locally
2. Rebuild image: `make build`
3. Test: `make verify`
4. Run: `make exec`

### Iterative Development

Mount your code directory for live editing:

```bash
docker run -it --rm \
  -v $(pwd):/app \
  lmr2-cfr:latest
```

### CI/CD Integration

The repository includes a GitHub Actions workflow (`.github/workflows/docker-build.yml`) that:
- Builds the image on every push
- Runs verification tests
- Pushes to Docker Hub
- Tags with git commit SHA and branch name

**Setup Instructions**: See `.github/DOCKER_HUB_SETUP.md` for step-by-step guide on:
- Creating Docker Hub access tokens
- Adding secrets to GitHub repository
- Configuring automated builds

## Advanced Usage

### Custom Environment Variables

Create a `.env` file:

```env
OMP_NUM_THREADS=8
NUMEXPR_MAX_THREADS=8
PYTHONUNBUFFERED=1
```

Use with docker-compose:

```yaml
env_file:
  - .env
```

### Multi-Container Setup

If you need additional services (e.g., database, monitoring):

```yaml
services:
  lmr2-app:
    # ... existing config ...
    depends_on:
      - postgres

  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: example
```

### Export/Share Image

```bash
# Export
make save

# Transfer the .tar.gz file to another machine

# Import
make load
```

## Resource Usage

**Expected Image Size**: 5-8 GB
**Build Time**: 15-30 minutes (first build)
**Rebuild Time**: 2-5 minutes (with cache)
**Runtime Memory**: 4-8 GB (depends on data size)
**Runtime CPU**: Scalable (use all available cores)

## Package Versions

The environment includes (see environment.yml for complete list):

- Python 3.11
- NumPy 1.26.4
- Pandas 1.5.3
- xarray 2023.1.0
- SciPy 1.13.1
- Matplotlib 3.9.2
- Cartopy 0.22.0
- CFR 2025.7.28
- And 300+ other packages

## Best Practices

1. **Always use volume mounts** for data directories
2. **Pin versions** in environment.yml for reproducibility
3. **Use BuildKit** for faster builds (`DOCKER_BUILDKIT=1`)
4. **Monitor resources** with `docker stats`
5. **Clean up regularly** with `make clean`
6. **Test after builds** with `make verify`

## Support & Documentation

- **Detailed Usage**: See `DOCKER_USAGE.md`
- **Docker Docs**: https://docs.docker.com/
- **Conda Docs**: https://docs.conda.io/
- **CFR Package**: Check CFR documentation

## Contributing

When modifying the Docker setup:

1. Test locally: `make build && make verify`
2. Update documentation
3. Test CI/CD workflow
4. Update version tags if needed

## License

Same as the parent project.

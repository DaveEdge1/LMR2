@echo off
REM Docker Run Script for LMR2 Project (Windows)
REM This script provides easy ways to run the Docker container on Windows

SETLOCAL EnableDelayedExpansion

SET IMAGE_NAME=lmr2-cfr
SET TAG=latest
SET CONTAINER_NAME=lmr2-container

REM Check if Docker is running
docker info >nul 2>&1
IF ERRORLEVEL 1 (
    echo Error: Docker is not running. Please start Docker Desktop.
    pause
    exit /b 1
)

REM Check if image exists
docker image inspect %IMAGE_NAME%:%TAG% >nul 2>&1
IF ERRORLEVEL 1 (
    echo Error: Image %IMAGE_NAME%:%TAG% not found.
    echo Please build the image first using docker-build.bat
    pause
    exit /b 1
)

:menu
echo.
echo ==========================================
echo LMR2 Docker Container
echo ==========================================
echo.
echo 1. Run interactive shell
echo 2. Run lmr_reproduce.py script
echo 3. Run with data volume mounts
echo 4. Verify environment
echo 5. Exit
echo.
SET /P choice="Enter your choice (1-5): "

IF "%choice%"=="1" GOTO shell
IF "%choice%"=="2" GOTO script
IF "%choice%"=="3" GOTO volumes
IF "%choice%"=="4" GOTO verify
IF "%choice%"=="5" GOTO end

echo Invalid choice. Please try again.
GOTO menu

:shell
echo.
echo Starting interactive shell...
docker run -it --rm --name %CONTAINER_NAME% %IMAGE_NAME%:%TAG%
GOTO menu

:script
echo.
echo Running lmr_reproduce.py...
docker run -it --rm --name %CONTAINER_NAME% ^
    -e OMP_NUM_THREADS=4 ^
    -e NUMEXPR_MAX_THREADS=4 ^
    %IMAGE_NAME%:%TAG% conda run -n cfr-env python lmr_reproduce.py
GOTO menu

:volumes
echo.
echo Starting container with volume mounts...
echo Current directory: %CD%
docker run -it --rm --name %CONTAINER_NAME% ^
    -v "%CD%\prev_data:/app/prev_data" ^
    -v "%CD%\cases:/app/cases" ^
    -v "%CD%\recons:/app/recons" ^
    -e OMP_NUM_THREADS=4 ^
    -e NUMEXPR_MAX_THREADS=4 ^
    %IMAGE_NAME%:%TAG%
GOTO menu

:verify
echo.
echo Verifying environment...
docker run --rm %IMAGE_NAME%:%TAG% conda run -n cfr-env python -c "import sys; import numpy as np; import pandas as pd; import xarray as xr; import netCDF4; import scipy; import matplotlib; import cartopy; import cfr; print('All core packages imported successfully!'); print(f'Python: {sys.version}'); print(f'NumPy: {np.__version__}'); print(f'CFR: {cfr.__version__}')"
echo.
pause
GOTO menu

:end
echo.
echo Goodbye!
ENDLOCAL
exit /b 0

@echo off
REM Docker Build Script for LMR2 Project (Windows)
REM This script provides a robust way to build and run the Docker container on Windows

SETLOCAL EnableDelayedExpansion

REM Configuration
SET IMAGE_NAME=lmr2-cfr
SET TAG=latest
IF NOT "%1"=="" SET TAG=%1
SET DOCKERFILE=.\Dockerfile

echo ==========================================
echo Building Docker Image: %IMAGE_NAME%:%TAG%
echo ==========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
IF ERRORLEVEL 1 (
    echo Error: Docker is not running. Please start Docker Desktop.
    pause
    exit /b 1
)

REM Check if Dockerfile exists
IF NOT EXIST "%DOCKERFILE%" (
    echo Error: Dockerfile not found at %DOCKERFILE%
    pause
    exit /b 1
)

REM Check if environment.yml exists
IF NOT EXIST ".\environment.yml" (
    echo Error: environment.yml not found
    pause
    exit /b 1
)

REM Build with BuildKit for better caching and performance
echo Starting Docker build...
echo.

SET DOCKER_BUILDKIT=1
docker build --progress=plain --tag %IMAGE_NAME%:%TAG% --file %DOCKERFILE% .

IF ERRORLEVEL 1 (
    echo.
    echo ==========================================
    echo Build Failed!
    echo ==========================================
    pause
    exit /b 1
) ELSE (
    echo.
    echo ==========================================
    echo Build Successful!
    echo Image: %IMAGE_NAME%:%TAG%
    echo ==========================================
    echo.
    echo To run the container:
    echo   docker run -it %IMAGE_NAME%:%TAG%
    echo.
    echo To run with mounted data directory:
    echo   docker run -it -v %CD%\data:/app/data %IMAGE_NAME%:%TAG%
    echo.
    echo To run your script:
    echo   docker run -it %IMAGE_NAME%:%TAG% conda run -n cfr-env python lmr_reproduce.py
    echo.
    pause
)

ENDLOCAL
